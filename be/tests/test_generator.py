"""Tests for the deterministic synthetic data generator."""
from __future__ import annotations

import pytest

from app.reconciliation import reconcile
from synth.generator import SyntheticDataGenerator

REQUIRED_FIELDS = {
    "shop_id", "gstin", "shop_name", "shop_category", "state_code",
    "gstin_valid", "upi_turnover", "gst_turnover", "purchases",
    "inventory_value", "cash_sales",
}


class TestDeterminism:
    def test_same_seed_same_output(self, generator):
        a = generator.generate(10, seed=42)
        b = generator.generate(10, seed=42)
        assert a == b

    def test_different_seed_different_output(self, generator):
        a = generator.generate(10, seed=42)
        b = generator.generate(10, seed=99)
        assert a != b

    def test_default_seed_is_42(self, generator):
        # Calling generate() without a seed uses the constructor seed (42).
        a = generator.generate(10)
        b = generator.generate(10, seed=42)
        assert a == b

    def test_round_trips_through_dataframe(self, generator):
        import pandas as pd

        shops = generator.generate(10, seed=42)
        df = generator.to_dataframe(shops)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert set(df.columns) == REQUIRED_FIELDS


class TestShape:
    def test_returns_requested_count(self, generator):
        assert len(generator.generate(10)) == 10
        assert len(generator.generate(3)) == 3

    def test_all_required_fields_present(self, generator):
        for shop in generator.generate(10):
            assert set(shop.keys()) == REQUIRED_FIELDS

    def test_shop_ids_are_sequential(self, generator):
        ids = [s["shop_id"] for s in generator.generate(10)]
        assert ids == list(range(10))

    def test_gstins_are_unique_for_small_n(self, generator):
        gstins = [s["gstin"] for s in generator.generate(10)]
        assert len(set(gstins)) == 10

    def test_invalid_gstin_shop_is_marked(self, generator):
        shops = generator.generate(10, seed=42)
        # Scenario index 2 is the invalid-GSTIN (rejected) shop.
        assert shops[2]["gstin_valid"] is False
        assert all(s["gstin_valid"] for i, s in enumerate(shops) if i != 2)


class TestPairCase:
    """The headline Stage-1 claim: two shops with the same UPI get different verdicts."""

    def test_shops_zero_and_one_share_upi(self, generator):
        shops = generator.generate(10, seed=42)
        assert shops[0]["upi_turnover"] == shops[1]["upi_turnover"]
        assert shops[0]["upi_turnover"] > 0

    def test_pair_shops_get_different_verdicts(self, generator, policy):
        shops = generator.generate(10, seed=42)
        v0 = reconcile(shops[0], policy)["verdict"]
        v1 = reconcile(shops[1], policy)["verdict"]
        assert v0 == "approved"
        assert v1 == "flagged"
        assert v0 != v1

    def test_pair_shops_differ_on_purchases_or_category(self, generator):
        shops = generator.generate(10, seed=42)
        assert (shops[0]["purchases"] != shops[1]["purchases"]) or (
            shops[0]["shop_category"] != shops[1]["shop_category"]
        )


class TestScenarioComposition:
    """The 10-shop golden set has the expected verdict mix."""

    def test_verdict_mix(self, generator, policy):
        shops = generator.generate(10, seed=42)
        verdicts = [reconcile(s, policy)["verdict"] for s in shops]
        assert verdicts.count("approved") == 5
        assert verdicts.count("flagged") == 4
        assert verdicts.count("rejected") == 1

    def test_invalid_gstin_shop_rejected(self, generator, policy):
        shops = generator.generate(10, seed=42)
        result = reconcile(shops[2], policy)
        assert result["verdict"] == "rejected"
        assert result["gstin_valid"] is False

    def test_upi_exceeds_scenario_flagged(self, generator, policy):
        shops = generator.generate(10, seed=42)
        # Scenario index 4: upi_exceeds_gst
        result = reconcile(shops[4], policy)
        assert result["verdict"] == "flagged"
        assert result["upi_turnover"] > result["gst_turnover"]
