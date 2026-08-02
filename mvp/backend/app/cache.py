import json
import sqlite3
import time
from contextlib import contextmanager

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS person_cache (
    cache_key TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(settings.cache_db_path)
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _key(name: str) -> str:
    return name.strip().lower()


def get(name: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT profile_json, created_at FROM person_cache WHERE cache_key = ?",
            (_key(name),),
        ).fetchone()
    if not row:
        return None
    profile_json, created_at = row
    age_hours = (time.time() - created_at) / 3600
    if age_hours > settings.cache_ttl_hours:
        return None
    return json.loads(profile_json)


def put(name: str, profile: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO person_cache (cache_key, profile_json, created_at) "
            "VALUES (?, ?, ?)",
            (_key(name), json.dumps(profile), time.time()),
        )
