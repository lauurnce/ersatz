"""Settings come from the environment and keys stay hidden."""

import pytest

from ersatz.settings import Settings


def test_defaults_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ERSATZ_LLM_MODEL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ersatz_llm_provider == "anthropic"
    assert settings.mouser_api_key.get_secret_value() == ""


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOUSER_API_KEY", "test-value")
    settings = Settings(_env_file=None)
    assert settings.mouser_api_key.get_secret_value() == "test-value"
    assert "test-value" not in repr(settings)
