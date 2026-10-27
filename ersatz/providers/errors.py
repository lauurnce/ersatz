"""Provider errors. Each message says what failed and what to do next."""


class ProviderError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider


class MissingCredentialsError(ProviderError):
    """A key needed by the provider is empty in the environment."""


class AuthError(ProviderError):
    """The provider rejected the credentials."""


class QuotaExceededError(ProviderError):
    """The provider kept answering 429 after every retry."""

    def __init__(self, provider: str, message: str, retry_after: float | None = None) -> None:
        super().__init__(provider, message)
        self.retry_after = retry_after


class ProviderUnavailableError(ProviderError):
    """Server errors or network failures continued after every retry."""


class ProviderResponseError(ProviderError):
    """The response was not in the expected shape, or the request was rejected."""


class NotSupportedError(ProviderError):
    """The provider does not offer this capability."""
