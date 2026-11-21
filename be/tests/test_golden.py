"""Golden test: the seed-42 10-shop dataset must reproduce the pinned verdicts.

This is a regression lock. The verdicts in tests/golden_expected.csv were
produced by the current (correct) generator + reconciler and must stay stable.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.policy import load_policy
from app.reconciliation import reconcile
from synth.generator import SyntheticDataGenerator

GOLDEN_CSV = Path(__file__).resolve().parent / "golden_expected.csv"


@pytest.fixture(scope="module")
def golden_df():
    return pd.read_csv(GOLDEN_CSV)


@pytest.fixture(scope="module")
def reconciled():
    policy = load_policy()
    gen = SyntheticDataGenerator(policy, seed=42)
    shops = gen.generate(10, seed=42)
    return [reconcile(s, policy) for s in shops]


class TestGoldenFile:
    def test_golden_file_has_ten_shops(self, golden_df):
        assert len(golden_df) == 10
        assert list(golden_df["shop_id"]) == list(range(10))

    def test_golden_verdicts_match_expected_mix(self, golden_df):
        counts = golden_df["verdict"].value_counts().to_dict()
        assert counts.get("approved") == 4
        assert counts.get("flagged") == 6


class TestGoldenReproducibility:
    def test_shop_ids_match(self, reconciled, golden_df):
        assert [r["shop_id"] for r in reconciled] == list(golden_df["shop_id"])

    def test_categories_match(self, reconciled, golden_df):
        assert [r["shop_category"] for r in reconciled] == list(
            golden_df["shop_category"]
        )

    def test_gstin_valid_flags_match(self, reconciled, golden_df):
        assert [r["gstin_valid"] for r in reconciled] == list(
            golden_df["gstin_valid"]
        )

    def test_verdicts_match(self, reconciled, golden_df):
        actual = [r["verdict"] for r in reconciled]
        expected = list(golden_df["verdict"])
        assert actual == expected, f"verdict mismatch: {actual} != {expected}"

    def test_pair_case_holds(self, reconciled):
        # Shops 0 and 1: same UPI inflow, different verdicts.
        assert reconciled[0]["upi_turnover"] == reconciled[1]["upi_turnover"]
        assert reconciled[0]["verdict"] != reconciled[1]["verdict"]
        assert reconciled[0]["verdict"] == "approved"
        assert reconciled[1]["verdict"] == "flagged"
