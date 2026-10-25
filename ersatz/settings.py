"""Settings loaded from the environment and an optional .env file.

Keys are never logged and never written to the cache. Empty values mean
the matching provider or feature is unavailable.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Names match the keys in .env.example."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    digikey_client_id: str = ""
    digikey_client_secret: SecretStr = SecretStr("")
    mouser_api_key: SecretStr = SecretStr("")
    nexar_client_id: str = ""
    nexar_client_secret: SecretStr = SecretStr("")

    anthropic_api_key: SecretStr = SecretStr("")
    ersatz_llm_provider: str = "anthropic"
    ersatz_llm_model: str = "claude-opus-5-5"

    openai_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")
    openrouter_api_key: SecretStr = SecretStr("")

    database_url: SecretStr = SecretStr("")
    ersatz_cache_dir: Path = Path("cache")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the settings, read once per process."""
    return Settings()
