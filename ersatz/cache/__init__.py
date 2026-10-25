"""Cache protocol with SQLite and Postgres implementations.

Provider data expires after 24 hours. Datasheet files and extraction
results are keyed by file hash and never expire.
"""
