"""Extraction prompt, versioned.

Change PROMPT_VERSION whenever the text changes, so cached extractions
made with an older prompt are not reused. The pages are sent as the same
pdfplumber text that quote verification reads (D-031).
"""

from ersatz.datasheets.pages import PageText
from ersatz.datasheets.schema import CATEGORY_FEATURES, MAX_QUOTE_CHARS
from ersatz.model.category import Category
from ersatz.model.parameter import CATEGORY_PARAMS, ParamName

PROMPT_VERSION = "1"

PARAM_HELP: dict[ParamName, str] = {
    ParamName.VIN: "recommended operating input voltage range, never absolute maximum",
    ParamName.VIN_ABS_MAX: "absolute maximum input voltage",
    ParamName.VOUT: "nominal output voltage for a fixed device",
    ParamName.VREF: "reference or feedback voltage for an adjustable device",
    ParamName.VOUT_ACCURACY: "output voltage accuracy or tolerance, in percent",
    ParamName.IOUT: "rated or maximum continuous output current",
    ParamName.DROPOUT: "dropout voltage; put the output current in conditions",
    ParamName.IQ: "quiescent, ground or supply current; say per amplifier or total in conditions",
    ParamName.ISHDN: "shutdown or standby current with the device disabled",
    ParamName.PSRR: "ripple rejection or PSRR; put the frequency in conditions",
    ParamName.COUT_MIN: "minimum output capacitance required for stability",
    ParamName.COUT_ESR: "output capacitor ESR range required for stability",
    ParamName.CHANNELS: "number of amplifiers in one package",
    ParamName.VSUPPLY: "operating supply voltage range from recommended operating conditions",
    ParamName.GBW: "gain bandwidth product",
    ParamName.SLEW_RATE: "slew rate",
    ParamName.VOS: "input offset voltage",
    ParamName.IBIAS: "input bias current",
    ParamName.VNOISE: "input voltage noise density; put the frequency in conditions",
    ParamName.IQ_PER_CHANNEL: "quiescent current per amplifier, when stated per amplifier",
    ParamName.MIN_STABLE_GAIN: "minimum closed-loop gain for stability",
    ParamName.TJ: "operating junction or ambient temperature range",
}

FEATURE_HELP = {
    "adjustable_output": "the device has an adjustable output set by resistors",
    "ceramic_cap_stable": "stated to be stable with ceramic output capacitors",
    "enable_pin": "the device has an enable or shutdown control pin",
    "rail_to_rail_input": "the input common-mode range includes both supply rails",
    "rail_to_rail_output": "the output swings to both supply rails",
    "unity_gain_stable": "the amplifier is stable at a gain of 1",
}

SYSTEM = f"""You extract component specifications from datasheet page text.

Rules:
- Use only the page text given. Never use outside knowledge.
- Copy every number exactly as printed. Do not convert units or round.
- Put each printed column in its own field: min, typ, max. Leave a field null
  when the datasheet has no value in that column. A range such as
  "2.5 V to 6 V" is min 2.5 and max 6.
- Every entry needs page and quote. The page is the number in the
  "=== PAGE n ===" marker. The quote is one contiguous piece of text copied
  character for character from that page, at most {MAX_QUOTE_CHARS} characters,
  and it must contain every number you report for that entry.
- When a value is printed at 25 degrees C and over the full temperature range,
  report two entries and state the temperature in conditions.
- When rows differ by device, output voltage or package, report one entry per
  row and name the row in variant.
- Absolute maximum ratings are never operating limits.
- Report a feature only when the text states it. Leave out anything the text
  does not state. Leaving a field out is better than guessing.
- Pinouts: one entry per package with every pin. Use OTHER when no listed
  function fits."""


def build_user_message(
    pages: list[PageText], selected: list[int], category: Category, device: str | None
) -> str:
    """Return the user message: what to extract, then the selected pages."""
    params = sorted(CATEGORY_PARAMS[category], key=lambda p: p.value)
    lines = [f"Category: {category.value}"]
    if device:
        lines.append(f"Target device: {device}. Report rows for this device only.")
    lines.append("Parameters:")
    lines += [f"- {p.value}: {PARAM_HELP[p]}" for p in params]
    lines.append("Features:")
    lines += [f"- {f.value}: {FEATURE_HELP[f.value]}" for f in CATEGORY_FEATURES[category]]
    lines.append("Also report every package with its pin count, and each package's pinout.")
    by_number = {p.page: p for p in pages}
    for number in selected:
        lines.append(f"\n=== PAGE {number} ===\n{by_number[number].text}")
    return "\n".join(lines)
