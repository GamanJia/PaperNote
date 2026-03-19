from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class RuntimeConfig:
    project_root: Path
    data_dir: Path
    searches_dir: Path
    exports_dir: Path
    cache_dir: Path
    config_dir: Path
    openai_api_key: str
    openai_base_url: str
    default_model_name: str
    openalex_mailto: str
    openalex_trust_env_proxy: bool
    ollama_base_url: str
    backend_host: str
    backend_port: int
    frontend_origins: List[str]


def load_runtime_config() -> RuntimeConfig:
    load_dotenv()

    project_root = Path(__file__).resolve().parents[3]
    data_dir = Path(os.getenv("PAPERNOTE_DATA_DIR", str(project_root / "data")))

    frontend_origins_raw = os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    frontend_origins = [item.strip() for item in frontend_origins_raw.split(",") if item.strip()]
    openalex_trust_env_proxy_raw = os.getenv("OPENALEX_TRUST_ENV_PROXY", "false").strip().lower()
    openalex_trust_env_proxy = openalex_trust_env_proxy_raw in {"1", "true", "yes", "on"}

    return RuntimeConfig(
        project_root=project_root,
        data_dir=data_dir,
        searches_dir=data_dir / "searches",
        exports_dir=data_dir / "exports",
        cache_dir=data_dir / "cache",
        config_dir=data_dir / "config",
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        default_model_name=os.getenv("DEFAULT_MODEL_NAME", "gpt-4o-mini"),
        openalex_mailto=os.getenv("OPENALEX_MAILTO", "").strip(),
        openalex_trust_env_proxy=openalex_trust_env_proxy,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        backend_host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        frontend_origins=frontend_origins,
    )
