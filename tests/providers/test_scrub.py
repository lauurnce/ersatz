"""Scrubbing of recorded traffic."""

import json

from ersatz.providers.scrub import REDACTED, scrub_body, scrub_headers


def test_sensitive_headers_are_redacted() -> None:
    headers = scrub_headers({"Authorization": "Bearer x", "X-DIGIKEY-Client-Id": "id", "A": "b"})
    assert headers == {"Authorization": REDACTED, "X-DIGIKEY-Client-Id": REDACTED, "A": "b"}


def test_nested_token_fields_are_redacted() -> None:
    body = json.dumps({"access_token": "t", "x": [{"client_secret": "s", "ok": 1}]}).encode()
    data = json.loads(scrub_body(body))
    assert data == {"access_token": REDACTED, "x": [{"client_secret": REDACTED, "ok": 1}]}


def test_literal_secret_values_are_replaced_in_text() -> None:
    assert scrub_body(b"key=abc123 in text", secrets=("abc123",)) == b"key=REDACTED in text"
