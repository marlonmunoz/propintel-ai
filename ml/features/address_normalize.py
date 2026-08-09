"""
Shared address normalization for BBL resolution.

Used by BOTH the offline index builder (ml/pipelines/build_address_bbl_index.py)
and the production resolver (backend/app/services/address_resolver.py, added in
a later phase). Importing one function from one place guarantees the accuracy
measured offline against the training spine is the accuracy served in
production — any drift here would silently invalidate that measurement.

NYC address sources spell the same address differently:
    spine (rolling sales)  : "16 EAST 80TH STREET, 2A"   "441 81ST STREET"
    PLUTO                  : "35-12 CORPORAL STONE ST"   "214-10 35 AVENUE"
    Mapbox (frontend)      : "16 East 80th Street"

normalize_address() reduces all of these to one canonical key so they can be
joined on equality. It deliberately does NOT try to be a general geocoder —
just consistent enough that the same physical lot normalizes to the same
string everywhere it appears.
"""

from __future__ import annotations

import re

# Longest-match-first: multi-word forms before the single words they contain.
_STREET_SUFFIXES: dict[str, str] = {
    "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "ROAD": "RD",
    "PLACE": "PL", "DRIVE": "DR", "LANE": "LN", "COURT": "CT",
    "PARKWAY": "PKWY", "SQUARE": "SQ", "TERRACE": "TER",
    "EXPRESSWAY": "EXPY", "HIGHWAY": "HWY", "CIRCLE": "CIR", "ALLEY": "ALY",
    "TURNPIKE": "TPKE", "CRESCENT": "CRES",
}
_DIRECTIONALS: dict[str, str] = {
    "EAST": "E", "WEST": "W", "NORTH": "N", "SOUTH": "S",
}

# PLUTO's 2-letter borough code -> the numeric borough code used everywhere
# else in this codebase (spine, ModelRegistry.BOROUGH_NAMES, the API schema).
PLUTO_BOROUGH_TO_NUM: dict[str, int] = {
    "MN": 1, "BX": 2, "BK": 3, "QN": 4, "SI": 5,
}

_ORDINAL_RE = re.compile(r"(\d+)(ST|ND|RD|TH)\b")
_NON_ALNUM_RE = re.compile(r"[^\w\s-]")
_MULTI_SPACE_RE = re.compile(r"\s+")
_UNIT_SUFFIX_RE = re.compile(r",.*$")


def normalize_address(raw: str | None) -> str | None:
    """Reduce a street address to a canonical matching key, or None if unusable.

    Steps (order matters):
      1. Drop anything after a comma — spine condo/coop rows carry a unit
         designator there (", 2A") that PLUTO's base-lot address never has.
      2. Uppercase, strip punctuation apart from the hyphen in Queens-style
         house numbers ("80-23").
      3. Collapse ordinal suffixes: "80TH" -> "80", matching PLUTO's "35" in
         "214-10 35 AVENUE" against the spine's "35TH AVENUE".
      4. Canonicalize street suffixes and directionals to one abbreviated form
         each, since sources mix "STREET"/"ST" and "EAST"/"E" inconsistently.
      5. Collapse whitespace.

    Returns None for blank/unparseable input so callers can abstain rather
    than match on an empty string.
    """
    if not raw or not str(raw).strip():
        return None

    text = _UNIT_SUFFIX_RE.sub("", str(raw)).upper()
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _ORDINAL_RE.sub(r"\1", text)

    tokens = [t for t in _MULTI_SPACE_RE.split(text.strip()) if t]
    tokens = [_STREET_SUFFIXES.get(t, t) for t in tokens]
    tokens = [_DIRECTIONALS.get(t, t) for t in tokens]

    normalized = " ".join(tokens).strip()
    return normalized or None


def pluto_borough_to_num(code: str | None) -> int | None:
    """PLUTO's 2-letter borough code -> the numeric code used elsewhere."""
    if not code:
        return None
    return PLUTO_BOROUGH_TO_NUM.get(str(code).strip().upper())
