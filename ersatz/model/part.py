"""The normalized part. It can only come from a provider record."""

from pydantic import BaseModel, Field, model_validator

from ersatz.model.category import Category
from ersatz.model.lifecycle import Lifecycle
from ersatz.model.package import Package, Pinout
from ersatz.model.parameter import Parameter, ParamName
from ersatz.model.source import SourceKind
from ersatz.model.sourced import Sourced


class Part(BaseModel, frozen=True):
    mpn: Sourced[str]
    manufacturer: Sourced[str]
    category: Sourced[Category] | None
    lifecycle: tuple[Sourced[Lifecycle], ...]
    package: Package | None
    pinout: Pinout | None = None
    parameters: dict[ParamName, Parameter] = Field(default_factory=dict)
    datasheet_url: Sourced[str] | None = None
    stock: tuple[Sourced[int], ...] = ()
    # Provider strings that could not be parsed, kept verbatim with their source.
    unparsed: dict[str, Sourced[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _from_provider(self) -> "Part":
        if self.mpn.source.kind is not SourceKind.PROVIDER:
            raise ValueError("a part number must come from a provider response")
        if self.manufacturer.source.kind is not SourceKind.PROVIDER:
            raise ValueError("a manufacturer must come from a provider response")
        for name, parameter in self.parameters.items():
            if parameter.name is not name:
                raise ValueError(f"parameter stored under {name} is {parameter.name}")
        return self
