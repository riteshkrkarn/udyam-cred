"""Tests for the deterministic synthetic data generator."""
from __future__ import annotations

import pytest

from app.reconciliation import reconcile
from synth.generator import SyntheticDataGenerator

REQUIRED_FIELDS = {
    "shop_id", "gstin", "shop_name", "shop_category", "state_code",
    "gstin_valid", "upi_turnover", "gst_turnover", "purchases",
    "opening_stock", "closing_stock", "inventory_value", "cash_sales",
    "true_health",
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

    def test_true_health_in_valid_range(self, generator):
        shops = generator.generate(10, seed=42)
        for shop in shops:
            assert 0.0 <= shop["true_health"] <= 1.0


class TestHealthDistribution:
    """Verify that true_health drives the verdict mix."""

    def test_healthy_shops_have_higher_health(self, generator):
        shops = generator.generate(10, seed=42)
        # Indices 0, 3, 5, 7, 9 should be healthy (health > 0.5)
        for idx in [0, 3, 5, 7, 9]:
            assert shops[idx]["true_health"] > 0.5

    def test_unhealthy_shops_have_lower_health(self, generator):
        shops = generator.generate(10, seed=42)
        # Indices 1, 2, 4, 6, 8 should be unhealthy (health <= 0.5)
        for idx in [1, 2, 4, 6, 8]:
            assert shops[idx]["true_health"] <= 0.5


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
        assert v0 != v1

    def test_pair_shops_differ_on_purchases_or_category(self, generator):
        shops = generator.generate(10, seed=42)
        assert (shops[0]["purchases"] != shops[1]["purchases"]) or (
            shops[0]["shop_category"] != shops[1]["shop_category"]
        )


class TestVerdictMix:
    """The 10-shop golden set has realistic verdicts from health-based generation."""

    def test_mostly_approved_and_flagged(self, generator, policy):
        shops = generator.generate(10, seed=42)
        verdicts = [reconcile(s, policy)["verdict"] for s in shops]
        # With true_health-based generation, we expect:
        # - 5 healthy shops (typically approve)
        # - 5 unhealthy shops (typically flag)
        approved_count = verdicts.count("approved")
        flagged_count = verdicts.count("flagged")
        assert approved_count >= 4  # At least 4 approvals from healthy shops
        assert flagged_count >= 3   # At least 3 flags from unhealthy shops
