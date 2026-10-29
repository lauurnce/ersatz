"""The client protocol and its result types."""

from typing import Any, Protocol

from pydantic import BaseModel


class LLMError(Exception):
    """The model call failed or returned something unusable."""


class Usage(BaseModel, frozen=True):
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class LLMResult(BaseModel, frozen=True):
    data: dict[str, Any]
    usage: Usage
    model: str
    request_id: str | None = None


class LLMClient(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResult:
        """Return one JSON object that follows `schema`."""
        ...
