# Providers

Terms, limits and sources are in DOMAIN.md section 5 and D-018. This page
covers how the adapters use them.

## Digi-Key (primary)

- API: Product Information v4. Product details by part number and keyword search.
- Auth: OAuth2 client credentials. The token is refreshed 60 seconds before it expires, and once more after a 401.
- Hosts: api.digikey.com, or sandbox-api.digikey.com when DIGIKEY_USE_SANDBOX=true.
- Limits: a token bucket of 100 calls per minute stays under the 120 per minute limit. The daily request budget is 900 of the 1,000 daily calls. Every attempt, including a retry, counts against the budget.
- Retries: 429, 5xx and network errors, up to 4 attempts with full jitter backoff. A Retry-After header sets the minimum wait.
- Errors: missing keys, rejected keys (401, 403), quota (429 after retries), budget spent, provider unavailable, unexpected response shape. Each message names the cause.
- Exact match: get_part returns a record only when the returned part number equals the query, ignoring case and surrounding spaces. A 404 or any other part number means not found.
- Parametric search: not enabled yet. It needs Digi-Key parameter filter IDs, which are mapped from local recordings first.

## Mouser (secondary)

Not implemented. The adapter is written after its terms are read (D-018, risk 8).

## Cache windows

| Data | Time-to-live |
|---|---|
| Part details | 24 hours |
| Search results | 24 hours |
| Datasheet files | none, keyed by file hash |
| Extraction results | none, keyed by file hash and extractor version |
| Request budget counters | 2 days |

The SQLite cache file is cache/ersatz.sqlite, which is git-ignored.

## Fixtures and recordings

- Committed fixtures in tests/fixtures/ are synthetic and use TEST- part numbers (D-019).
- `ersatz lookup --record` and `make smoke` write scrubbed responses to cache/recordings/. Authorization and client ID headers, token fields and the literal key values are replaced with REDACTED. Recordings are never committed.
- Tests run with sockets disabled. The live check runs only through `make smoke` with keys in .env and skips when CI is set.
