"""Anthropic client using structured outputs (output_config.format).

Thinking is left at the model default and effort is set explicitly. The
JSON schema in the request constrains the reply; the caller still
validates it with Pydantic.
"""

import json
from typing import Any, Literal

import anthropic
from anthropic.types import OutputConfigParam

from ersatz.llm.base import LLMError, LLMResult, Usage

Effort = Literal["low", "medium", "high", "xhigh", "max"]


class AnthropicClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        effort: Effort = "high",
        client: anthropic.Anthropic | None = None,
    ) -> None:
        if not api_key and client is None:
            raise LLMError("ANTHROPIC_API_KEY is empty; set it in .env to run extraction")
        self._client = client or anthropic.Anthropic(api_key=api_key, max_retries=3)
        self._model = model
        self._effort = effort

    @property
    def provider(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResult:
        config: OutputConfigParam = {
            "effort": self._effort,
            "format": {"type": "json_schema", "schema": schema},
        }
        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config=config,
            ) as stream:
                message = stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise LLMError(f"anthropic: HTTP {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"anthropic: connection failed: {exc}") from exc
        if message.stop_reason != "end_turn":
            raise LLMError(f"anthropic: stopped with {message.stop_reason}")
        text = "".join(block.text for block in message.content if block.type == "text")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("anthropic: reply is not valid JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("anthropic: reply is not a JSON object")
        usage = message.usage
        return LLMResult(
            data=data,
            usage=Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_input_tokens=usage.cache_read_input_tokens or 0,
                cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
            ),
            model=message.model,
            request_id=message._request_id,
        )
