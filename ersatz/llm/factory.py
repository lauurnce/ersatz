"""Build the extraction client named in settings."""

from ersatz.llm.anthropic import AnthropicClient
from ersatz.llm.base import LLMClient, LLMError
from ersatz.settings import Settings


def make_llm(settings: Settings) -> LLMClient:
    provider = settings.ersatz_llm_provider
    if provider == "anthropic":
        return AnthropicClient(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=settings.ersatz_llm_model,
        )
    raise LLMError(f"unknown ERSATZ_LLM_PROVIDER {provider!r}; v0.1 supports anthropic")
