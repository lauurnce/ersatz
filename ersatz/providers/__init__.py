"""Provider protocol and distributor adapters.

Adapters share one HTTP client with retries and a rate limiter, and they
declare which capabilities they support.
"""

from ersatz.providers.base import Capability, ParametricQuery, Provider, ProviderRecord
from ersatz.providers.errors import (
    AuthError,
    MissingCredentialsError,
    NotSupportedError,
    ProviderError,
    ProviderResponseError,
    ProviderUnavailableError,
    QuotaExceededError,
)

__all__ = [
    "AuthError",
    "Capability",
    "MissingCredentialsError",
    "NotSupportedError",
    "ParametricQuery",
    "Provider",
    "ProviderError",
    "ProviderRecord",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "QuotaExceededError",
]
