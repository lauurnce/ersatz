from types import SimpleNamespace
from typing import Any, cast

import anthropic
import pytest
from pydantic import SecretStr

from ersatz.llm.anthropic import AnthropicClient
from ersatz.llm.base import LLMError
from ersatz.llm.factory import make_llm
from ersatz.settings import Settings


class FakeStream:
    def __init__(self, message: Any) -> None:
        self.message = message

    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get_final_message(self) -> Any:
        return self.message


class FakeMessages:
    def __init__(self, message: Any) -> None:
        self.message = message
        self.kwargs: dict[str, Any] = {}

    def stream(self, **kwargs: Any) -> FakeStream:
        self.kwargs = kwargs
        return FakeStream(self.message)


def message(text: str, stop_reason: str = "end_turn") -> Any:
    usage = SimpleNamespace(
        input_tokens=1200,
        output_tokens=300,
        cache_read_input_tokens=None,
        cache_creation_input_tokens=None,
    )
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=usage,
        model="claude-opus-5-5",
        _request_id="req_1",
    )


def client_for(msg: Any) -> tuple[AnthropicClient, FakeMessages]:
    messages = FakeMessages(msg)
    fake = cast(anthropic.Anthropic, SimpleNamespace(messages=messages))
    return AnthropicClient(api_key="", model="claude-opus-5-5", client=fake), messages


def test_request_uses_structured_output_and_effort() -> None:
    client, messages = client_for(message('{"parameters": []}'))
    schema = {"type": "object"}
    result = client.complete_json("sys", "user", schema, 16000)
    assert result.data == {"parameters": []}
    assert result.usage.input_tokens == 1200
    assert result.usage.cache_read_input_tokens == 0
    assert result.request_id == "req_1"
    config = messages.kwargs["output_config"]
    assert config["format"] == {"type": "json_schema", "schema": schema}
    assert config["effort"] == "high"
    assert messages.kwargs["system"] == "sys"
    assert "thinking" not in messages.kwargs


@pytest.mark.parametrize(
    ("text", "stop", "error"),
    [
        ("{}", "max_tokens", "stopped with max_tokens"),
        ("{}", "refusal", "stopped with refusal"),
        ("not json", "end_turn", "not valid JSON"),
        ("[1, 2]", "end_turn", "not a JSON object"),
    ],
)
def test_unusable_replies_raise(text: str, stop: str, error: str) -> None:
    client, _ = client_for(message(text, stop))
    with pytest.raises(LLMError, match=error):
        client.complete_json("s", "u", {}, 100)


def test_missing_key_is_reported() -> None:
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY is empty"):
        AnthropicClient(api_key="", model="claude-opus-5-5")


def test_factory_builds_the_configured_client() -> None:
    settings = Settings(
        _env_file=None,
        anthropic_api_key=SecretStr("test-key"),
        ersatz_llm_model="claude-opus-5-5",
    )
    llm = make_llm(settings)
    assert (llm.provider, llm.model) == ("anthropic", "claude-opus-5-5")


def test_factory_rejects_unknown_provider() -> None:
    settings = Settings(_env_file=None, ersatz_llm_provider="other")
    with pytest.raises(LLMError, match="unknown ERSATZ_LLM_PROVIDER"):
        make_llm(settings)
