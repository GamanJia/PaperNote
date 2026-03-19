from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.repositories.file_storage import FileStorage
from app.schemas.history import HistorySummary
from app.utils.text_utils import short_text


class SearchHistoryRepository:
    def __init__(self, searches_dir: Path, storage: FileStorage) -> None:
        self.searches_dir = searches_dir
        self.storage = storage
        self.storage.ensure_dirs(searches_dir)
        self.index_path = searches_dir / "index.json"

    def _load_index(self) -> list[dict[str, Any]]:
        return self.storage.read_json(self.index_path, default=[])

    def _save_index(self, index: list[dict[str, Any]]) -> None:
        self.storage.write_json_atomic(self.index_path, index)

    def _build_title(self, record: dict[str, Any]) -> str:
        parsed = record.get("parsed_query", {})
        topic = parsed.get("topic") or ""
        if topic:
            return short_text(topic, 64)
        keywords = parsed.get("keywords") or []
        if keywords:
            return short_text(", ".join(keywords[:4]), 64)
        return "PaperNote 检索记录"

    def _build_markdown(self, record: dict[str, Any]) -> str:
        parsed = record.get("parsed_query", {})
        stats = record.get("stats", {})
        results = record.get("results", [])

        lines = [
            f"# 搜索记录 {record['id']}",
            "",
            f"- 创建时间: {record['created_at']}",
            f"- 主题: {parsed.get('topic', '')}",
            f"- 候选论文数: {stats.get('total_candidates', 0)}",
            f"- 最终结果数: {stats.get('final_results', 0)}",
            "",
            "## 查询条件",
            "",
            "```json",
            json.dumps(record.get("request", {}), ensure_ascii=False, indent=2),
            "```",
            "",
            "## 结果概览",
            "",
            "| 标题 | 来源 | 年份 | 相关性 | 标签 |",
            "| --- | --- | --- | --- | --- |",
        ]

        for item in results:
            title = (item.get("title") or "").replace("|", " ")
            source = item.get("source", "")
            year = str(item.get("year", ""))
            score = str(item.get("relevance_score", ""))
            tags = ", ".join(item.get("tags") or [])
            lines.append(f"| {title} | {source} | {year} | {score} | {tags} |")

        return "\n".join(lines) + "\n"

    def _make_summary(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "title": self._build_title(record),
            "created_at": record["created_at"],
            "total_candidates": int(record.get("stats", {}).get("total_candidates", 0)),
            "final_results": int(record.get("stats", {}).get("final_results", 0)),
        }

    def generate_search_id(self) -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("search_%Y%m%d_%H%M%S_%f")

    def save_search(self, record: dict[str, Any]) -> HistorySummary:
        search_id = record.get("id") or self.generate_search_id()
        record["id"] = search_id
        record["created_at"] = record.get("created_at") or datetime.now(timezone.utc).isoformat()
        record["title"] = self._build_title(record)
        record["exports"] = record.get("exports") or []

        json_path = self.searches_dir / f"{search_id}.json"
        md_path = self.searches_dir / f"{search_id}.md"
        self.storage.write_json_atomic(json_path, record)
        self.storage.write_text_atomic(md_path, self._build_markdown(record))

        summary = self._make_summary(record)
        index = [item for item in self._load_index() if item.get("id") != search_id]
        index.insert(0, summary)
        self._save_index(index)

        return HistorySummary.model_validate(summary)

    def list_history(self) -> list[HistorySummary]:
        index = self._load_index()
        return [HistorySummary.model_validate(item) for item in index]

    def get_search(self, search_id: str) -> dict[str, Any] | None:
        path = self.searches_dir / f"{search_id}.json"
        data = self.storage.read_json(path, default=None)
        return data

    def delete_search(self, search_id: str) -> bool:
        json_path = self.searches_dir / f"{search_id}.json"
        md_path = self.searches_dir / f"{search_id}.md"
        if not json_path.exists() and not md_path.exists():
            return False

        self.storage.delete_file(json_path)
        self.storage.delete_file(md_path)

        index = [item for item in self._load_index() if item.get("id") != search_id]
        self._save_index(index)
        return True

    def add_export_record(self, search_id: str, export_record: dict[str, Any]) -> None:
        record = self.get_search(search_id)
        if not record:
            return

        exports = record.get("exports") or []
        exports.insert(0, export_record)
        record["exports"] = exports[:20]

        json_path = self.searches_dir / f"{search_id}.json"
        md_path = self.searches_dir / f"{search_id}.md"
        self.storage.write_json_atomic(json_path, record)
        self.storage.write_text_atomic(md_path, self._build_markdown(record))
