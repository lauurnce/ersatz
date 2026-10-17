"""Pull candidate part numbers out of pasted chatbot text.

A token counts as a part number when it is made of capital letters, digits
and the joiners - / . # +, holds at least one letter and one digit, and is
not a value with a unit (3.3V, 500mA), a package name, or a common
specification word. Lowercase words are never part numbers here. Every
token found is checked against providers; nothing is completed or fixed.
"""

import re

from ersatz.normalize.packages import package_group

_TOKEN = re.compile(r"(?<![A-Za-z0-9])[A-Z0-9][A-Z0-9\-/.#+]*[A-Z0-9#+](?![A-Za-z0-9])")
_VALUE = re.compile(
    r"^[+\-]?\d+(\.\d+)?(\-\d+(\.\d+)?)?-?"
    r"(V|MV|KV|A|MA|UA|NA|HZ|KHZ|MHZ|GHZ|W|MW|F|UF|NF|PF|DB|DBM|C|K|PPM|MS|US|NS|BIT|BITS|X)?$",
    re.IGNORECASE,
)
STOP = frozenset(
    {
        "AEC-Q100",
        "AEC-Q101",
        "AEC-Q200",
        "ISO9001",
        "ISO26262",
        "IATF16949",
        "ROHS",
        "ROHS2",
        "REACH",
        "JEDEC",
        "ESD",
        "HBM",
        "CDM",
        "I2C",
        "I2S",
        "SPI",
        "UART",
        "USB",
        "USB2",
        "USB3",
        "PCIE",
        "DDR3",
        "DDR4",
        "LPDDR4",
        "CAN-FD",
        "LIN",
        "GPIO",
        "ADC",
        "DAC",
        "PWM",
        "LDO",
        "PSRR",
        "GBW",
        "CMRR",
        "RRIO",
        "MOSFET",
        "BJT",
        "JFET",
        "CMOS",
        "IC",
        "PCB",
        "QFN",
        "DFN",
        "SOIC",
        "SOT",
        "MSOP",
        "TSSOP",
        "PDIP",
        "WSON",
        "SON",
        "BGA",
        "LGA",
        "MSL1",
        "MSL2",
        "MSL3",
        "2D",
        "3D",
        "4K",
        "5G",
        "4G",
        "LTE",
        "AC",
        "DC",
        "AC-DC",
        "DC-DC",
        "EOL",
        "NRND",
        "LTB",
        "PCN",
        "FAQ",
        "PDF",
        "URL",
        "API",
    }
)
MIN_LEN = 4
MAX_LEN = 40


def _is_package(token: str) -> bool:
    return package_group(token).status == "MATCHED"


def is_part_number(token: str) -> bool:
    if not MIN_LEN <= len(token) <= MAX_LEN:
        return False
    if not (re.search(r"[A-Z]", token) and re.search(r"\d", token)):
        return False
    if token.upper() in STOP or _VALUE.match(token):
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):  # a date
        return False
    return not _is_package(token)


def extract_mpns(text: str) -> list[str]:
    """Return the part numbers in `text`, in order of first appearance, without duplicates."""
    seen: set[str] = set()
    found: list[str] = []
    for match in _TOKEN.finditer(text):
        token = match.group(0).rstrip(".")
        if is_part_number(token) and token not in seen:
            seen.add(token)
            found.append(token)
    return found
