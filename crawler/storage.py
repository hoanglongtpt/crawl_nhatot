from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS crawl_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_listing_id TEXT NOT NULL UNIQUE,
    source_ad_id TEXT,
    category_code INTEGER,
    region_code INTEGER,
    published_at TEXT,
    refreshed_at TEXT,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    contact_phone_status TEXT NOT NULL DEFAULT 'unavailable',
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS crawl_checkpoints (
    partition_key TEXT PRIMARY KEY,
    current_offset INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    last_error TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    cutoff_at TEXT NOT NULL,
    status TEXT NOT NULL,
    received_items INTEGER NOT NULL DEFAULT 0,
    accepted_items INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);
"""


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def start_run(self, started_at: str, cutoff_at: str) -> int:
        cursor = self.connection.execute(
            "INSERT INTO crawl_runs(started_at, cutoff_at, status) VALUES (?, ?, 'running')",
            (started_at, cutoff_at),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        finished_at: str,
        status: str,
        received: int,
        accepted: int,
        error: str | None = None,
    ) -> None:
        self.connection.execute(
            """UPDATE crawl_runs
               SET finished_at=?, status=?, received_items=?, accepted_items=?, error_summary=?
               WHERE id=?""",
            (finished_at, status, received, accepted, error, run_id),
        )
        self.connection.commit()

    def checkpoint(self, key: str) -> int:
        row = self.connection.execute(
            "SELECT current_offset FROM crawl_checkpoints WHERE partition_key=?",
            (key,),
        ).fetchone()
        return int(row[0]) if row else 0

    def save_checkpoint(
        self, key: str, offset: int, status: str, updated_at: str, error: str | None = None
    ) -> None:
        self.connection.execute(
            """INSERT INTO crawl_checkpoints(partition_key,current_offset,status,last_error,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(partition_key) DO UPDATE SET
                 current_offset=excluded.current_offset,
                 status=excluded.status,
                 last_error=excluded.last_error,
                 updated_at=excluded.updated_at""",
            (key, offset, status, error, updated_at),
        )
        self.connection.commit()

    def upsert(self, item: dict[str, Any]) -> None:
        self.connection.execute(
            """INSERT INTO crawl_items(
                 source_listing_id,source_ad_id,category_code,region_code,published_at,
                 refreshed_at,payload_json,payload_hash,contact_phone_status,fetched_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source_listing_id) DO UPDATE SET
                 source_ad_id=excluded.source_ad_id,
                 category_code=excluded.category_code,
                 region_code=excluded.region_code,
                 published_at=excluded.published_at,
                 refreshed_at=excluded.refreshed_at,
                 payload_json=excluded.payload_json,
                 payload_hash=excluded.payload_hash,
                 contact_phone_status=excluded.contact_phone_status,
                 fetched_at=excluded.fetched_at""",
            (
                item["source_listing_id"],
                item.get("source_ad_id"),
                item.get("category_code"),
                item.get("region_code"),
                item.get("published_at"),
                item.get("refreshed_at"),
                json.dumps(item["raw_payload"], ensure_ascii=False),
                item["payload_hash"],
                item["contact_phone_status"],
                item["fetched_at"],
            ),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

