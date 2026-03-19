from __future__ import annotations

from pathlib import Path

from app.repositories.file_storage import FileStorage
from app.schemas.llm import LLMConfig, LLMProviderType
from app.schemas.settings import AppSettings


class SettingsRepository:
    def __init__(
        self,
        config_dir: Path,
        storage: FileStorage,
        default_openai_base_url: str,
        default_model_name: str,
        default_ollama_base_url: str,
    ) -> None:
        self.config_dir = config_dir
        self.storage = storage
        self.storage.ensure_dirs(config_dir)
        self.path = config_dir / "settings.json"
        self.default_openai_base_url = default_openai_base_url
        self.default_model_name = default_model_name
        self.default_ollama_base_url = default_ollama_base_url

    def default_settings(self) -> AppSettings:
        return AppSettings(
            default_model=LLMConfig(
                provider_type=LLMProviderType.OPENAI_COMPATIBLE,
                base_url=self.default_openai_base_url,
                model_name=self.default_model_name,
                api_key=None,
                temperature=0.2,
                max_tokens=1024,
            ),
            enabled_sources=["openalex", "arxiv"],
            default_export_format="csv",
        )

    def load_settings(self) -> AppSettings:
        payload = self.storage.read_json(self.path, default=None)
        if not payload:
            settings = self.default_settings()
            self.save_settings(settings)
            return settings

        try:
            settings = AppSettings.model_validate(payload)
        except Exception:
            settings = self.default_settings()
            self.save_settings(settings)
            return settings

        # 向后兼容：若历史 settings 仍是初始占位默认值，则优先对齐当前 .env 默认配置。
        needs_update = False
        if (
            settings.default_model.provider_type == LLMProviderType.OPENAI_COMPATIBLE
            and settings.default_model.base_url == "https://api.openai.com/v1"
            and self.default_openai_base_url
            and self.default_openai_base_url != "https://api.openai.com/v1"
        ):
            settings.default_model.base_url = self.default_openai_base_url
            needs_update = True

        if (
            settings.default_model.model_name == "gpt-4o-mini"
            and self.default_model_name
            and self.default_model_name != "gpt-4o-mini"
        ):
            settings.default_model.model_name = self.default_model_name
            needs_update = True

        if needs_update:
            self.save_settings(settings)

        return settings

    def save_settings(self, settings: AppSettings) -> AppSettings:
        self.storage.write_json_atomic(self.path, settings.model_dump())
        return settings
