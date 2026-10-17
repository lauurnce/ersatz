"""What the rules compare: one part's values from provider and datasheet.

When both give a value, the datasheet value is used (docs/ARCHITECTURE.md
section 3) and the provider value is kept as the fallback. Only HIGH
confidence datasheet values are used; LOW values never feed a rule.
"""

from pydantic import BaseModel, Field

from ersatz.datasheets.validate import Confidence, Extraction
from ersatz.model.category import Category
from ersatz.model.lifecycle import Lifecycle, furthest
from ersatz.model.package import Package, Pinout
from ersatz.model.parameter import Parameter, ParamName
from ersatz.model.part import Part
from ersatz.model.sourced import Sourced
from ersatz.normalize.packages import package_group


class PartProfile(BaseModel, frozen=True):
    part: Part
    parameters: dict[ParamName, Parameter] = Field(default_factory=dict)
    features: dict[str, Sourced[bool]] = Field(default_factory=dict)
    pinout: Pinout | None = None

    @property
    def mpn(self) -> str:
        return self.part.mpn.value

    @property
    def manufacturer(self) -> str:
        return self.part.manufacturer.value

    @property
    def category(self) -> Category | None:
        return self.part.category.value if self.part.category else None

    @property
    def package(self) -> Package | None:
        return self.part.package

    @property
    def lifecycle(self) -> Lifecycle:
        return furthest([s.value for s in self.part.lifecycle])

    @property
    def stock(self) -> int:
        return sum(s.value for s in self.part.stock)


def profile(part: Part, extraction: Extraction | None = None) -> PartProfile:
    """Merge provider values with HIGH confidence datasheet values."""
    parameters = dict(part.parameters)
    features: dict[str, Sourced[bool]] = {}
    pinout = part.pinout
    if extraction is not None:
        seen: set[ParamName] = set()
        for item in extraction.parameters:
            name = item.parameter.name
            if item.confidence is Confidence.HIGH and name not in seen:
                parameters[name] = item.parameter
                seen.add(name)
        for feature in extraction.features:
            features.setdefault(feature.name, Sourced(value=feature.value, source=feature.source))
        if part.package is not None:
            for extracted in extraction.pinouts:
                if extracted.confidence is Confidence.HIGH and _same_package(
                    extracted.package, part.package
                ):
                    pinout = extracted.pinout
                    break
    return PartProfile(part=part, parameters=parameters, features=features, pinout=pinout)


def _same_package(name: str, package: Package) -> bool:
    match = package_group(name)
    return match.group is not None and match.group.name == package.group
