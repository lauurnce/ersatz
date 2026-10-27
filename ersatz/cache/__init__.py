"""Cache protocol with SQLite and Postgres implementations.

Provider data expires after 24 hours. Datasheet files and extraction
results are keyed by file hash and never expire.
"""

from ersatz.cache.base import DEFAULT_TTL, Cache, CacheEntry, DataKind
from ersatz.cache.sqlite import SqliteCache

__all__ = ["DEFAULT_TTL", "Cache", "CacheEntry", "DataKind", "SqliteCache"]
