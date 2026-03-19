from __future__ import annotations

from functools import lru_cache

from app.connectors.arxiv_connector import ArxivConnector
from app.connectors.base import BaseConnector
from app.connectors.openalex_connector import OpenAlexConnector
from app.core.config import RuntimeConfig, load_runtime_config
from app.repositories.cache_repository import CacheRepository
from app.repositories.file_storage import FileStorage
from app.repositories.search_history_repository import SearchHistoryRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.export_service import ExportService
from app.services.llm_service import LLMService
from app.services.paper_ranker_service import PaperRankerService
from app.services.paper_search_service import PaperSearchService
from app.services.query_parser_service import QueryParserService
from app.services.search_orchestrator_service import SearchOrchestratorService


@lru_cache(maxsize=1)
def get_runtime_config() -> RuntimeConfig:
    config = load_runtime_config()
    FileStorage().ensure_dirs(
        config.data_dir,
        config.searches_dir,
        config.exports_dir,
        config.cache_dir,
        config.config_dir,
    )
    return config


@lru_cache(maxsize=1)
def get_file_storage() -> FileStorage:
    return FileStorage()


@lru_cache(maxsize=1)
def get_cache_repository() -> CacheRepository:
    config = get_runtime_config()
    return CacheRepository(cache_dir=config.cache_dir, storage=get_file_storage())


@lru_cache(maxsize=1)
def get_search_history_repository() -> SearchHistoryRepository:
    config = get_runtime_config()
    return SearchHistoryRepository(searches_dir=config.searches_dir, storage=get_file_storage())


@lru_cache(maxsize=1)
def get_settings_repository() -> SettingsRepository:
    config = get_runtime_config()
    return SettingsRepository(
        config_dir=config.config_dir,
        storage=get_file_storage(),
        default_openai_base_url=config.openai_base_url,
        default_model_name=config.default_model_name,
        default_ollama_base_url=config.ollama_base_url,
    )


@lru_cache(maxsize=1)
def get_connectors() -> dict[str, BaseConnector]:
    return {
        "openalex": OpenAlexConnector(),
        "arxiv": ArxivConnector(),
    }


@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    return LLMService(get_runtime_config())


@lru_cache(maxsize=1)
def get_query_parser_service() -> QueryParserService:
    return QueryParserService(get_llm_service())


@lru_cache(maxsize=1)
def get_paper_search_service() -> PaperSearchService:
    return PaperSearchService(get_connectors(), get_cache_repository())


@lru_cache(maxsize=1)
def get_paper_ranker_service() -> PaperRankerService:
    return PaperRankerService(get_llm_service(), get_cache_repository())


@lru_cache(maxsize=1)
def get_export_service() -> ExportService:
    return ExportService(get_runtime_config().exports_dir)


@lru_cache(maxsize=1)
def get_search_orchestrator_service() -> SearchOrchestratorService:
    return SearchOrchestratorService(
        query_parser_service=get_query_parser_service(),
        paper_search_service=get_paper_search_service(),
        paper_ranker_service=get_paper_ranker_service(),
        history_repository=get_search_history_repository(),
    )
