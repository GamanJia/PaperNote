from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.repositories.file_storage import FileStorage


class CacheRepository:
    def __init__(self, cache_dir: Path, storage: FileStorage) -> None:
        self.cache_dir = cache_dir
        self.storage = storage
        self.storage.ensure_dirs(cache_dir)

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Any | None:
        path = self._path_for_key(key)
        payload = self.storage.read_json(path, default=None)
        if not payload:
            return None

        expires_at_raw = payload.get("expires_at")
        if not expires_at_raw:
            return None

        expires_at = datetime.fromisoformat(expires_at_raw)
        if datetime.now(timezone.utc) > expires_at:
            self.storage.delete_file(path)
            return None

        return payload.get("data")

    def set(self, key: str, data: Any, ttl_seconds: int) -> None:
        path = self._path_for_key(key)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        payload = {
            "expires_at": expires_at.isoformat(),
            "data": data,
        }
        self.storage.write_json_atomic(path, payload)
