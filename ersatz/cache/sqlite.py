"""SQLite cache for local use. The file lives under the cache directory."""

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from ersatz.cache.base import DEFAULT_TTL, CacheEntry, DataKind

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    payload BLOB NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    PRIMARY KEY (kind, key)
)
"""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SqliteCache:
    def __init__(self, path: Path | str, clock: Callable[[], datetime] = _utcnow) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute(_SCHEMA)
        self._clock = clock

    def get(self, kind: DataKind, key: str) -> CacheEntry | None:
        row = self._db.execute(
            "SELECT payload, created_at, expires_at FROM entries WHERE kind = ? AND key = ?",
            (kind.value, key),
        ).fetchone()
        if row is None:
            return None
        payload, created, expires = row
        expires_at = datetime.fromisoformat(expires) if expires else None
        if expires_at is not None and expires_at <= self._clock():
            return None
        return CacheEntry(
            kind=kind,
            key=key,
            payload=payload,
            created_at=datetime.fromisoformat(created),
            expires_at=expires_at,
        )

    def put(
        self,
        kind: DataKind,
        key: str,
        payload: bytes,
        ttl: timedelta | Literal["default"] | None = "default",
    ) -> None:
        """Store a payload. Without ttl, the default for the kind applies."""
        now = self._clock()
        lifetime = DEFAULT_TTL[kind] if ttl == "default" else ttl
        expires = (now + lifetime).isoformat() if lifetime is not None else None
        with self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?)",
                (kind.value, key, payload, now.isoformat(), expires),
            )

    def purge_expired(self) -> int:
        """Delete expired entries and return how many were removed."""
        with self._db:
            cursor = self._db.execute(
                "DELETE FROM entries WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (self._clock().isoformat(),),
            )
        return cursor.rowcount

    def close(self) -> None:
        self._db.close()
