"""GSTIN (Goods and Services Tax Identification Number) validator.

GSTIN structure (15 chars):
    [0:2]   state code, two digits (valid range 01-38)
    [2:7]   PAN letters, 5 uppercase letters
    [7:11]  PAN digits, 4 digits
    [11]    PAN final letter
    [12]    entity code, 1 alphanumeric
    [13]    'Z' (constant)
    [14]    check digit (alphanumeric)

Checksum algorithm (alternating weights 1, 2, 1, 2, ... starting with 1):
    1. Map each of the first 14 chars to a value: 0-9 -> 0-9, A-Z -> 10-35.
    2. For char at index i, weight = 1 if i is even else 2.
    3. product = value * weight; add (product // 36) + (product % 36) to the sum
       (i.e. sum the base-36 digits of the product).
    4. check_value = (36 - (sum % 36)) % 36; the check digit is the char at that
       index of "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ".
"""
from __future__ import annotations

import re

CODE_POINTS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
MOD = 36
GSTIN_LENGTH = 15

# Valid Indian state codes for GST: 01-38 (no 00, no 39+).
_VALID_STATE_CODES = {f"{i:02d}" for i in range(1, 39)}

# 2 digits, 5 letters, 4 digits, 1 letter, 1 alnum entity, Z, 1 alnum check digit.
_GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$")


class GSTINError(ValueError):
    """Raised when a GSTIN fails validation."""


def _char_value(c: str) -> int:
    if c not in CODE_POINTS:
        raise GSTINError(f"Invalid character in GSTIN: {c!r}")
    return CODE_POINTS.index(c)


def compute_check_digit(gstin14: str) -> str:
    """Return the check digit for the first 14 characters of a GSTIN."""
    if not isinstance(gstin14, str):
        raise GSTINError("GSTIN prefix must be a string")
    gstin14 = gstin14.strip().upper()
    if len(gstin14) != 14:
        raise GSTINError(
            f"Need exactly 14 characters to compute check digit, got {len(gstin14)}"
        )
    total = 0
    for i, c in enumerate(gstin14):
        val = _char_value(c)
        weight = 1 if i % 2 == 0 else 2  # alternating 1, 2, 1, 2, ...
        product = val * weight
        total += (product // MOD) + (product % MOD)  # base-36 digit sum of product
    check_value = (MOD - (total % MOD)) % MOD
    return CODE_POINTS[check_value]


def validate_gstin(gstin: str, check_state: bool = True) -> str:
    """Validate a GSTIN, returning the normalised (uppercased) value.

    Raises GSTINError on any failure. With check_state=False the state-code
    range check is skipped (format + checksum still enforced).
    """
    if not isinstance(gstin, str):
        raise GSTINError("GSTIN must be a string")
    g = gstin.strip().upper()
    if len(g) != GSTIN_LENGTH:
        raise GSTINError(f"GSTIN must be {GSTIN_LENGTH} characters, got {len(g)}")
    if not _GSTIN_RE.match(g):
        raise GSTINError("GSTIN does not match the expected pattern")
    if check_state and g[:2] not in _VALID_STATE_CODES:
        raise GSTINError(f"Invalid state code: {g[:2]}")
    expected = compute_check_digit(g[:14])
    if g[14] != expected:
        raise GSTINError(f"Checksum mismatch: expected {expected!r}, got {g[14]!r}")
    return g


def is_valid_gstin(gstin: str, check_state: bool = True) -> bool:
    """True if the GSTIN is valid, False otherwise (never raises)."""
    try:
        validate_gstin(gstin, check_state=check_state)
        return True
    except GSTINError:
        return False


def make_valid_gstin(prefix14: str) -> str:
    """Return a 15-char GSTIN by appending the correct check digit to prefix14."""
    p = prefix14.strip().upper()
    if len(p) != 14:
        raise GSTINError(f"prefix must be 14 chars, got {len(p)}")
    # Validate the prefix characters are in the code-point alphabet.
    for c in p:
        _char_value(c)
    return p + compute_check_digit(p)


def state_code(gstin: str) -> str | None:
    """Return the 2-digit state code if the GSTIN is valid, else None."""
    if is_valid_gstin(gstin):
        return gstin.strip().upper()[:2]
    return None
