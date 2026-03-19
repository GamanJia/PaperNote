from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.schemas.paper import PaperResult


class ExportService:
    def __init__(self, exports_dir: Path) -> None:
        self.exports_dir = exports_dir
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def _rows(self, results: list[PaperResult]) -> list[dict]:
        rows: list[dict] = []
        for item in results:
            rows.append(
                {
                    "title": item.title,
                    "authors": ", ".join(item.authors),
                    "year": item.year,
                    "published_date": item.published_date,
                    "venue": item.venue,
                    "source": item.source,
                    "doi": item.doi,
                    "url": item.url,
                    "pdf_url": item.pdf_url,
                    "abstract": item.abstract,
                    "tags": ", ".join(item.tags),
                    "relevance_score": item.relevance_score,
                    "summary": item.summary,
                    "reason": item.reason,
                    "innovation": item.innovation,
                    "match_points": ", ".join(item.match_points),
                }
            )
        return rows

    def _to_markdown(self, rows: list[dict]) -> str:
        if not rows:
            return "# PaperNote Export\n\n_No data_\n"

        headers = list(rows[0].keys())
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            line_values = []
            for header in headers:
                raw_value = str(row.get(header, "") or "")
                line_values.append(raw_value.replace("\n", " ").replace("|", " "))
            lines.append("| " + " | ".join(line_values) + " |")
        return "\n".join(lines) + "\n"

    def export_results(self, results: list[PaperResult], fmt: str, file_prefix: str | None = None) -> dict:
        rows = self._rows(results)
        df = pd.DataFrame(rows)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = file_prefix or "papernote_export"

        if fmt == "markdown":
            file_name = f"{base}_{timestamp}.md"
            output_path = self.exports_dir / file_name
            output_path.write_text(self._to_markdown(rows), encoding="utf-8")
        elif fmt == "xlsx":
            file_name = f"{base}_{timestamp}.xlsx"
            output_path = self.exports_dir / file_name
            df.to_excel(output_path, index=False)
        else:
            file_name = f"{base}_{timestamp}.csv"
            output_path = self.exports_dir / file_name
            df.to_csv(output_path, index=False, encoding="utf-8")

        return {
            "file_name": file_name,
            "format": fmt,
            "row_count": len(rows),
            "created_at": datetime.now(timezone.utc),
            "absolute_path": str(output_path.resolve()),
        }
