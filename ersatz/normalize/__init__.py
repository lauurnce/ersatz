"""Pure functions that map provider and datasheet text to the model.

Covers unit parsing to SI base units, package groups, categories and
lifecycle status.
"""

from ersatz.normalize.categories import CategoryMatch, map_category
from ersatz.normalize.lifecycle import map_lifecycle
from ersatz.normalize.packages import PackageMatch, package_group
from ersatz.normalize.part import Normalized, normalize
from ersatz.normalize.units import ParsedValue, UnitParseError, parse_value

__all__ = [
    "CategoryMatch",
    "Normalized",
    "PackageMatch",
    "ParsedValue",
    "UnitParseError",
    "map_category",
    "map_lifecycle",
    "normalize",
    "package_group",
    "parse_value",
]
