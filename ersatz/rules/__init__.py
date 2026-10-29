"""Form, fit and function rules as data files.

Each YAML file mirrors a section of docs/DOMAIN.md, and every rule keeps
the ID used there.
"""

from functools import cache
from importlib.resources import files
from typing import Any

import yaml


@cache
def load(name: str) -> dict[str, Any]:
    """Load a rules file by name, for example load("packages")."""
    text = files(__name__).joinpath(f"{name}.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"rules file {name}.yaml is not a mapping")
    return data
