from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from facestudio.assets.models import AssetRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    modified_time REAL NOT NULL,
    UNIQUE(root_path, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_assets_filename ON assets(filename);
CREATE INDEX IF NOT EXISTS idx_assets_extension ON assets(extension);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
"""


class AssetDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def replace_root(self, root: Path, records: Iterable[AssetRecord]) -> int:
        root_string = str(root.resolve())
        rows = [
            (
                root_string,
                record.relative_path,
                record.filename,
                record.extension,
                record.asset_type,
                record.size_bytes,
                record.modified_time,
            )
            for record in records
        ]

        with self._connect() as connection:
            connection.execute(
                "DELETE FROM assets WHERE root_path = ?",
                (root_string,),
            )
            connection.executemany(
                """
                INSERT INTO assets (
                    root_path,
                    relative_path,
                    filename,
                    extension,
                    asset_type,
                    size_bytes,
                    modified_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def search(
        self,
        query: str = "",
        asset_type: str = "",
        extension: str = "",
        limit: int = 5000,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        parameters: list[object] = []

        if query.strip():
            clauses.append(
                "(filename LIKE ? OR relative_path LIKE ?)"
            )
            wildcard = f"%{query.strip()}%"
            parameters.extend([wildcard, wildcard])

        if asset_type.strip():
            clauses.append("asset_type = ?")
            parameters.append(asset_type.strip())

        if extension.strip():
            normalised = extension.strip().lower()
            if not normalised.startswith("."):
                normalised = "." + normalised
            clauses.append("extension = ?")
            parameters.append(normalised)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, limit))

        with self._connect() as connection:
            return connection.execute(
                f"""
                SELECT
                    root_path,
                    relative_path,
                    filename,
                    extension,
                    asset_type,
                    size_bytes,
                    modified_time
                FROM assets
                {where}
                ORDER BY asset_type, filename
                LIMIT ?
                """,
                parameters,
            ).fetchall()

    def counts_by_type(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT asset_type, COUNT(*) AS total
                FROM assets
                GROUP BY asset_type
                ORDER BY total DESC, asset_type
                """
            ).fetchall()
        return {str(row["asset_type"]): int(row["total"]) for row in rows}

    def extensions(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT extension
                FROM assets
                WHERE extension <> ''
                ORDER BY extension
                """
            ).fetchall()
        return [str(row["extension"]) for row in rows]

    def total_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM assets"
            ).fetchone()
        return int(row["total"])
