"""Digi-Key adapter: OAuth2 client credentials, product details, keyword search."""

from ersatz.providers.digikey.adapter import (
    PRODUCTION_URL,
    SANDBOX_URL,
    DigiKeyProvider,
    parse_product,
)
from ersatz.providers.digikey.auth import TokenManager

__all__ = ["PRODUCTION_URL", "SANDBOX_URL", "DigiKeyProvider", "TokenManager", "parse_product"]
