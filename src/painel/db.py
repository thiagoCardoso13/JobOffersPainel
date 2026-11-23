"""DuckDB storage: keeps the raw JSON of every offer (raw layer)."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "offers.duckdb"


def connect(path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_offers (
            source      VARCHAR,
            offer_id    VARCHAR,
            query       VARCHAR,
            fetched_at  TIMESTAMP DEFAULT now(),
            payload     JSON,
            PRIMARY KEY (source, offer_id)
        )
        """
    )
    return con


def upsert_offers(con, source: str, query: str, offers: list[dict]) -> int:
    """Insert new offers and replace existing ones (idempotent). Returns how many were processed."""
    for o in offers:
        con.execute(
            "INSERT OR REPLACE INTO raw_offers (source, offer_id, query, payload) VALUES (?, ?, ?, ?)",
            [source, str(o["id"]), query, json.dumps(o, ensure_ascii=False)],
        )
    return len(offers)
