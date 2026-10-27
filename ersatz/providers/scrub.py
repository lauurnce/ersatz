"""Remove keys and tokens from recorded provider traffic.

Recordings are written only under cache/recordings/ and never committed.
They are scrubbed anyway, so a copied file cannot leak a key.
"""

import json
from collections.abc import Iterable, Mapping
from typing import Any

SENSITIVE_HEADERS = frozenset(
    {"authorization", "x-digikey-client-id", "cookie", "set-cookie", "x-api-key"}
)
SENSITIVE_FIELDS = frozenset(
    {"access_token", "refresh_token", "client_id", "client_secret", "apikey", "api_key"}
)
REDACTED = "REDACTED"


def scrub_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {k: (REDACTED if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}


def _scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (REDACTED if k.lower() in SENSITIVE_FIELDS else _scrub_value(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def scrub_body(body: bytes, secrets: Iterable[str] = ()) -> bytes:
    """Redact sensitive JSON fields and any literal secret values."""
    try:
        text = json.dumps(_scrub_value(json.loads(body)), sort_keys=True)
    except (ValueError, UnicodeDecodeError):
        text = body.decode("utf-8", errors="replace")
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return text.encode()
