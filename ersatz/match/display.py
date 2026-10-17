"""Human-readable values and sources for diff tables."""

from ersatz.model.parameter import Parameter
from ersatz.model.source import Source, SourceKind

_PREFIXES = [
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "u"),
    (1e-9, "n"),
    (1e-12, "p"),
    (1e-15, "f"),
]
_SCALED = {"V", "A", "Hz", "F", "ohm", "V/s", "V/Hz**0.5"}
_LABEL = {"V/Hz**0.5": "V/rtHz", "percent": "%", "degC": "degC", "": ""}


def number(value: float, unit: str) -> str:
    label = _LABEL.get(unit, unit)
    if unit in _SCALED and value != 0:
        if unit == "V/s":
            return f"{value / 1e6:.4g} V/us"
        for factor, prefix in _PREFIXES:
            if abs(value) >= factor * 0.9995:
                return f"{value / factor:.4g} {prefix}{label}"
        factor, prefix = _PREFIXES[-1]
        return f"{value / factor:.4g} {prefix}{label}"
    return f"{value:.4g} {label}".strip()


def parameter(p: Parameter | None) -> str:
    if p is None:
        return "-"
    parts = [
        f"{slot} {number(v, p.unit)}"
        for slot in ("min", "typ", "max")
        if (v := getattr(p, slot)) is not None
    ]
    text = ", ".join(parts)
    conditions = {k: v for k, v in p.conditions.items() if k in ("I", "f", "T", "text")}
    if conditions:
        text += " (" + "; ".join(f"{k}={v}" for k, v in conditions.items()) + ")"
    return text


def source(s: Source | None) -> str:
    if s is None:
        return "-"
    if s.kind is SourceKind.DATASHEET:
        rev = f" {s.revision}" if s.revision else ""
        return f"datasheet{rev} p{s.page}"
    return f"{s.provider} {str(s.response_id)[:10]}"
