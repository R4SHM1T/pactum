"""Parsing for the short duration strings used in freshness rules."""
from __future__ import annotations

import re
from datetime import timedelta

_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhdw])\s*$", re.IGNORECASE)

_UNITS = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
}


def parse_duration(text: str) -> timedelta:
    """Turn a string such as '2d', '12h' or '30m' into a timedelta."""
    match = _PATTERN.match(text)
    if not match:
        raise ValueError(f"could not parse duration: {text!r}")
    value, unit = match.groups()
    return timedelta(**{_UNITS[unit.lower()]: float(value)})
