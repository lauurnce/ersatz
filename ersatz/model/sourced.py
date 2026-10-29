"""A value paired with the source it came from."""

from pydantic import BaseModel

from ersatz.model.source import Source


class Sourced[T](BaseModel, frozen=True):
    value: T
    source: Source
