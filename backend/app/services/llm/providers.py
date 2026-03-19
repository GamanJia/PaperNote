from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.schemas.llm import LLMConfig
from app.utils.json_utils import safe_json_loads


class BaseLLMProvider(ABC):
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError

    async def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        text = await self.generate_text(prompt=prompt, system_prompt=system_prompt)
        return safe_json_loads(text, fallback={})


class OpenAICompatibleProvider(BaseLLMProvider):
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.base_url:
            raise ValueError("OpenAI-compatible provider requires base_url")
        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(endpoint, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> dict[str, Any]:
        if not self.config.base_url:
            return {"ok": False, "detail": "missing base_url"}
        endpoint = f"{self.config.base_url.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(endpoint, headers=self._headers())
            response.raise_for_status()
            return {"ok": True, "detail": "model endpoint reachable"}
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        response_data = await self._request(payload)
        choices = response_data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


class OllamaProvider(BaseLLMProvider):
    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.base_url:
            raise ValueError("Ollama provider requires base_url")
        endpoint = f"{self.config.base_url.rstrip('/')}/api/chat"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> dict[str, Any]:
        if not self.config.base_url:
            return {"ok": False, "detail": "missing base_url"}
        endpoint = f"{self.config.base_url.rstrip('/')}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(endpoint)
            response.raise_for_status()
            return {"ok": True, "detail": "ollama service reachable"}
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    async def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        response_data = await self._request(payload)
        message = response_data.get("message") or {}
        content = message.get("content")
        if content:
            return str(content)
        return str(response_data.get("response") or "")
