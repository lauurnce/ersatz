"""Synthetic parts for matching tests. Every part number starts with TEST-."""

from datetime import UTC, datetime
from typing import Any

from ersatz.match.profile import PartProfile
from ersatz.model import (
    UNITS,
    Category,
    Lifecycle,
    Package,
    Parameter,
    ParamName,
    Part,
    Pin,
    PinFunction,
    Pinout,
    Source,
    Sourced,
)
from ersatz.normalize.packages import package_group

NOW = datetime(2026, 10, 17, tzinfo=UTC)


def source(mpn: str) -> Source:
    return Source.from_response("digikey", mpn.encode(), NOW, url=f"https://example.invalid/{mpn}")


def p(name: str, mpn: str = "TEST", **values: Any) -> Parameter:
    conditions = values.pop("conditions", {})
    return Parameter(
        name=ParamName(name),
        unit=UNITS[ParamName(name)],
        conditions=conditions,
        source=source(mpn),
        **values,
    )


def pinout(mpn: str, *pins: tuple[str, str, int | None]) -> Pinout:
    return Pinout(
        pins=tuple(Pin(number=n, function=PinFunction(f), channel=ch) for n, f, ch in pins),
        source=source(mpn),
    )


def part(
    mpn: str,
    category: Category,
    package: str | None,
    params: dict[str, dict[str, Any]] | None = None,
    lifecycle: Lifecycle = Lifecycle.ACTIVE,
    pins: tuple[tuple[str, str, int | None], ...] | None = None,
    features: dict[str, bool] | None = None,
    stock: int = 1000,
    manufacturer: str = "Test Semi",
    height: float | None = None,
) -> PartProfile:
    src = source(mpn)
    pkg = None
    if package is not None:
        match = package_group(package)
        pkg = Package(
            raw_name=package,
            group=match.group.name if match.group else None,
            pin_count=match.pin_count,
            height_max_mm=height
            if height is not None
            else (match.group.height_max_mm if match.group else None),
            source=src,
        )
    parameters = {ParamName(k): p(k, mpn, **v) for k, v in (params or {}).items()}
    the_part = Part(
        mpn=Sourced(value=mpn, source=src),
        manufacturer=Sourced(value=manufacturer, source=src),
        category=Sourced(value=category, source=src),
        lifecycle=(Sourced(value=lifecycle, source=src),),
        package=pkg,
        pinout=pinout(mpn, *pins) if pins else None,
        parameters=parameters,
        stock=(Sourced(value=stock, source=src),),
    )
    return PartProfile(
        part=the_part,
        parameters=parameters,
        features={k: Sourced(value=v, source=src) for k, v in (features or {}).items()},
        pinout=the_part.pinout,
    )


LDO_PINS: tuple[tuple[str, str, int | None], ...] = (
    ("1", "IN", None),
    ("2", "GND", None),
    ("3", "EN", None),
    ("4", "NC", None),
    ("5", "OUT", None),
)

LDO_PARAMS: dict[str, dict[str, Any]] = {
    "vin": {"min": 2.5, "max": 6.0},
    "vin_abs_max": {"max": 6.5},
    "vout": {"typ": 3.3},
    "iout": {"max": 0.3},
    "dropout": {"typ": 0.25, "max": 0.35, "conditions": {"I": "0.3 A"}},
    "iq": {"typ": 50e-6, "max": 80e-6},
    "ishdn": {"max": 1e-6},
    "psrr": {"typ": 60, "conditions": {"f": "1000 Hz"}},
    "vout_accuracy": {"max": 2},
}

LDO_FEATURES = {"adjustable_output": False, "ceramic_cap_stable": True, "enable_pin": True}

DUAL_PINS: tuple[tuple[str, str, int | None], ...] = (
    ("1", "OUT", 1),
    ("2", "INN", 1),
    ("3", "INP", 1),
    ("4", "VEE", None),
    ("5", "INP", 2),
    ("6", "INN", 2),
    ("7", "OUT", 2),
    ("8", "VCC", None),
)

OPAMP_PARAMS: dict[str, dict[str, Any]] = {
    "channels": {"typ": 2},
    "vsupply": {"min": 3, "max": 30},
    "gbw": {"typ": 1e6},
    "slew_rate": {"typ": 0.5e6},
    "vos": {"typ": 2e-3, "max": 7e-3},
    "ibias": {"typ": 20e-9, "max": 250e-9},
    "vnoise": {"typ": 40e-9, "conditions": {"f": "1000 Hz"}},
    "iq_per_channel": {"typ": 350e-6, "max": 600e-6},
}

OPAMP_FEATURES = {
    "rail_to_rail_input": False,
    "rail_to_rail_output": False,
    "unity_gain_stable": True,
}


def ldo(mpn: str, **overrides: Any) -> PartProfile:
    params = {**LDO_PARAMS, **overrides.pop("params", {})}
    features = {**LDO_FEATURES, **overrides.pop("features", {})}
    kwargs: dict[str, Any] = {"package": "SOT-23-5", "pins": LDO_PINS, **overrides}
    return part(mpn, Category.LDO, params=params, features=features, **kwargs)


def opamp(mpn: str, **overrides: Any) -> PartProfile:
    params = {**OPAMP_PARAMS, **overrides.pop("params", {})}
    features = {**OPAMP_FEATURES, **overrides.pop("features", {})}
    kwargs: dict[str, Any] = {"package": "SOIC-8", "pins": DUAL_PINS, **overrides}
    return part(mpn, Category.OPAMP, params=params, features=features, **kwargs)
