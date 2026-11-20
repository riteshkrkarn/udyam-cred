"""Tests for the GSTIN validator (format, state code, checksum)."""
from __future__ import annotations

import pytest

from app.gstin import (
    GSTINError,
    compute_check_digit,
    is_valid_gstin,
    make_valid_gstin,
    state_code,
    validate_gstin,
)

# Verified-valid GSTINs (state code + the AAACR5049K1Z PAN structure + correct
# check digit computed by the same algorithm the validator uses).
VALID_GSTINS = [
    "01AAACR5049K1ZJ",  # state 01
    "07AAACR5049K1Z7",  # state 07
    "27AAACR5049K1Z5",  # state 27
    "29AAACR5049K1Z1",  # state 29
    "33AAACR5049K1ZC",  # state 33
    "36AAACR5049K1Z6",  # state 36
    "38AAACR5049K1Z2",  # state 38 (upper edge of valid range)
]

# Invalid GSTINs and the reason each fails.
INVALID_GSTINS = [
    ("27AAACR5049K1Z", "too short (14 chars)"),
    ("27AAACR5049K1Z55", "too long (16 chars)"),
    ("27AAACR5049K1Z0", "wrong check digit (correct is 5)"),
    ("27AA1CR5049K1Z5", "digit where a letter is required (bad pattern)"),
    ("27AAACR5049K1Z-", "invalid character as check digit"),
    ("00AAACR5049K1Z" + "0", "state code 00 out of range"),
    ("39AAACR5049K1Z" + "0", "state code 39 out of range"),
]


class TestValidGSTIN:
    @pytest.mark.parametrize("gstin", VALID_GSTINS)
    def test_valid_gstins_pass(self, gstin):
        assert is_valid_gstin(gstin) is True

    @pytest.mark.parametrize("gstin", VALID_GSTINS)
    def test_validate_returns_uppercased(self, gstin):
        assert validate_gstin(gstin) == gstin
        # case-insensitive input is normalised
        assert validate_gstin(gstin.lower()) == gstin

    def test_state_code_extracted(self):
        assert state_code("27AAACR5049K1Z5") == "27"
        assert state_code("38AAACR5049K1Z2") == "38"


class TestInvalidGSTIN:
    @pytest.mark.parametrize("gstin,reason", INVALID_GSTINS)
    def test_invalid_gstins_fail(self, gstin, reason):
        assert is_valid_gstin(gstin) is False, reason

    @pytest.mark.parametrize("gstin,reason", INVALID_GSTINS)
    def test_validate_raises(self, gstin, reason):
        with pytest.raises(GSTINError):
            validate_gstin(gstin)

    def test_non_string_rejected(self):
        assert is_valid_gstin(None) is False
        with pytest.raises(GSTINError):
            validate_gstin(12345)

    def test_empty_string_rejected(self):
        assert is_valid_gstin("") is False


class TestChecksumInternals:
    def test_check_digit_round_trip(self):
        # A correct check digit makes the GSTIN valid.
        prefix = "27AAACR5049K1Z"
        full = prefix + compute_check_digit(prefix)
        assert is_valid_gstin(full) is True

    def test_make_valid_gstin(self):
        # make_valid_gstin appends the correct check digit.
        full = make_valid_gstin("27AAACR5049K1Z")
        assert len(full) == 15
        assert is_valid_gstin(full) is True

    def test_alternating_weights_start_at_one(self):
        # Index 0 carries weight 1, index 1 weight 2. Confirm by changing the
        # weight-1 position vs a weight-2 position produces different sums is
        # implicit; here we assert the documented property: a single-character
        # change at a weight-1 position is detectable (checksum changes).
        base = "27AAACR5049K1Z"
        d0 = compute_check_digit(base)
        # Changing position 0 (state digit, weight 1) by +1 must change the digit
        changed = "28AAACR5049K1Z"
        d1 = compute_check_digit(changed)
        assert d0 != d1

    def test_bad_state_skipped_when_check_state_false(self):
        # With check_state=False, a structurally+checksum-valid GSTIN with a
        # bad state code still validates.
        g = make_valid_gstin("00AAACR5049K1Z")
        assert is_valid_gstin(g, check_state=False) is True
        assert is_valid_gstin(g, check_state=True) is False
