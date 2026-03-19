from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class LLMProviderType(str, Enum):
    OPENAI_COMPATIBLE = "openai-compatible"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    provider_type: LLMProviderType = LLMProviderType.OPENAI_COMPATIBLE
    base_url: str | None = None
    model_name: str = "gpt-4o-mini"
    api_key: str | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=64, le=8192)
