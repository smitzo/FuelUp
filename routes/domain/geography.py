"""Scoped geographic identifiers for Indian reference prices."""

import re
import unicodedata

ALIASES = {
    "bangalore": "bengaluru",
    "bombay": "mumbai",
    "madras": "chennai",
    "calcutta": "kolkata",
    "new-delhi": "delhi",
    "nct-of-delhi": "delhi",
    "national-capital-territory-of-delhi": "delhi",
    "orissa": "odisha",
    "pondicherry": "puducherry",
}


def geographic_slug(value):
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    slug = re.sub(r"[^\w]+", "-", value, flags=re.UNICODE).strip("-_")
    return ALIASES.get(slug, slug)


def scoped_geography_id(country, state="", locality=""):
    parts = [geographic_slug(value) for value in (country, state, locality)]
    if not parts[0] or (locality and not parts[1]):
        raise ValueError("A locality reference requires a country and state.")
    result = "/".join(part for part in parts if part)
    if len(result) > 160:
        raise ValueError("Geographic identifier is too long.")
    return result
