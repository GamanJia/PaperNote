from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class FileStorage:
    def ensure_dirs(self, *dirs: Path) -> None:
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def write_json_atomic(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            encoding="utf-8",
            delete=False,
            suffix=".tmp",
        ) as tmp_file:
            json.dump(data, tmp_file, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp_file.name)
        os.replace(tmp_path, path)

    def write_text_atomic(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            encoding="utf-8",
            delete=False,
            suffix=".tmp",
        ) as tmp_file:
            tmp_file.write(text)
            tmp_path = Path(tmp_file.name)
        os.replace(tmp_path, path)

    def delete_file(self, path: Path) -> None:
        if path.exists():
            path.unlink()
