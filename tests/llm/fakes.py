"""Fake language model clients. They never touch the network."""

import json
from collections.abc import Callable
from typing import Any

from ersatz.llm.base import LLMError, LLMResult, Usage

Reply = dict[str, Any] | Exception


class FakeLLM:
    """Returns scripted replies in order and records every request."""

    def __init__(
        self,
        *replies: Reply,
        model: str = "claude-opus-5-5",
        usage: Usage | None = None,
        responder: Callable[[str, str], Reply] | None = None,
    ) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self._model = model
        self._usage = usage or Usage(input_tokens=1000, output_tokens=200)
        self._responder = responder

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return self._model

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> LLMResult:
        self.requests.append(
            {"system": system, "user": user, "schema": schema, "max_tokens": max_tokens}
        )
        reply = self._responder(system, user) if self._responder else self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        json.dumps(reply)
        return LLMResult(data=reply, usage=self._usage, model=self._model, request_id="req_fake")


def failing(message: str = "fake failure") -> LLMError:
    return LLMError(message)
