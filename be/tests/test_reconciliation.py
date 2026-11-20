"""Tests for the reconciliation engine and its verdict logic."""
from __future__ import annotations

import pytest

from app.gstin import make_valid_gstin
from app.reconciliation import reconcile, reconcile_many
from app.policy import PolicyError

VALID_GSTIN = make_valid_gstin("27AAACR5049K1Z")  # 27AAACR5049K1Z5


def make_shop(**overrides) -> dict:
    """A minimal consistent shop; any field can be overridden."""
    base = {
        "shop_id": 0,
        "gstin": VALID_GSTIN,
        "shop_category": "kirana_without_inventory",  # margin 10% (point)
        "purchases": 900_000.0,  # goods_sold = 900_000; expected = 900_000 / (1 - 0.10) = 1_000_000
        "gst_turnover": 1_000_000.0,  # = 900_000 / (1 - 0.10) -> midpoint -> approved
        "upi_turnover": 500_000.0,
        "inventory_value": 100_000.0,
        "cash_sales": 500_000.0,
    }
    base.update(overrides)
    return base


class TestApproved:
    def test_consistent_shop_approved(self, policy):
        result = reconcile(make_shop(), policy)
        assert result["verdict"] == "approved"
        assert result["gstin_valid"] is True
        # expected_sales = goods_sold / (1 - margin); margin 0.10 -> 900_000/(1-0.10) = 1_000_000
        assert result["expected_sales_low"] == pytest.approx(900_000.0 / (1.0 - 0.10), rel=1e-4)
        assert result["expected_sales_high"] == pytest.approx(900_000.0 / (1.0 - 0.10), rel=1e-4)

    def test_band_midpoint_with_range_category(self, policy):
        # loose_goods margin 14-30%; midpoint 22%.
        shop = make_shop(
            shop_category="loose_goods",
            purchases=1_000_000.0,  # goods_sold = 1_000_000; expected_mid = 1_000_000 / (1 - 0.22) ~= 1_282_051
            gst_turnover=1_000_000.0 / (1.0 - 0.22),  # midpoint expected -> approved
            upi_turnover=100_000.0,
        )
        result = reconcile(shop, policy)
        assert result["verdict"] == "approved"


class TestRejected:
    def test_invalid_gstin_rejected(self, policy):
        shop = make_shop(gstin="27AAACR5049K1Z0")  # wrong check digit
        result = reconcile(shop, policy)
        assert result["verdict"] == "rejected"
        assert result["gstin_valid"] is False

    def test_empty_gstin_rejected(self, policy):
        shop = make_shop(gstin="")
        result = reconcile(shop, policy)
        assert result["verdict"] == "rejected"


class TestFlagged:
    def test_sales_suppression_flagged(self, policy):
        # Declared sales far below the expected band -> flagged.
        shop = make_shop(
            shop_category="loose_goods",  # 14-30%
            purchases=1_500_000.0,
            gst_turnover=400_000.0,  # well below expected_low = 1.5m/(1-0.14) ~= 1.74m
            upi_turnover=200_000.0,
        )
        result = reconcile(shop, policy)
        assert result["verdict"] == "flagged"
        assert "suppression" in result["reason"]

    def test_upi_exceeds_declared_flagged(self, policy):
        shop = make_shop(
            shop_category="beverages_impulse",
            purchases=1_000_000.0,
            gst_turnover=800_000.0,
            upi_turnover=1_000_000.0,  # > declared GST
        )
        result = reconcile(shop, policy)
        assert result["verdict"] == "flagged"
        assert "exceeds" in result["reason"]

    def test_declared_above_band_flagged(self, policy):
        # Declared sales above the expected band (margin too low for the category).
        shop = make_shop(
            shop_category="personal_care",  # 12-20%
            purchases=1_000_000.0,
            gst_turnover=1_300_000.0,  # expected_high = 1m/(1-0.12) ~= 1.136m, band_high ~= 1.142m -> above
            upi_turnover=100_000.0,
        )
        result = reconcile(shop, policy)
        assert result["verdict"] == "flagged"
        assert "above" in result["reason"]


class TestFormula:
    def test_expected_sales_uses_inverse_formula(self, policy):
        # expected_sales = goods_sold / (1 - margin)
        shop = make_shop(
            shop_category="kirana_with_inventory",  # margin 15%
            purchases=1_000_000.0,
            gst_turnover=1_000_000.0 / (1.0 - 0.15),
            upi_turnover=100_000.0,
        )
        result = reconcile(shop, policy)
        # expected = 1_000_000 / (1 - 0.15) for both low and high (point margin)
        assert result["expected_sales_low"] == pytest.approx(1_000_000.0 / (1.0 - 0.15), rel=1e-4)
        assert result["expected_sales_high"] == pytest.approx(1_000_000.0 / (1.0 - 0.15), rel=1e-4)

    def test_range_band_orders_correctly(self, policy):
        shop = make_shop(
            shop_category="loose_goods",  # 14-30%
            purchases=1_000_000.0,
            gst_turnover=1_000_000.0 / (1.0 - 0.22),
            upi_turnover=100_000.0,
        )
        result = reconcile(shop, policy)
        # lower margin -> lower expected; low uses margin_low (0.14)
        assert result["expected_sales_low"] == pytest.approx(1_000_000.0 / (1.0 - 0.14), rel=1e-4)
        assert result["expected_sales_high"] == pytest.approx(1_000_000.0 / (1.0 - 0.30), rel=1e-4)
        assert result["expected_sales_low"] < result["expected_sales_high"]


class TestReconcileMany:
    def test_preserves_order_and_count(self, policy, shops):
        results = reconcile_many(shops, policy)
        assert len(results) == len(shops)
        assert [r["shop_id"] for r in results] == [s["shop_id"] for s in shops]

    def test_unknown_category_raises(self, policy):
        with pytest.raises(PolicyError):
            reconcile(make_shop(shop_category="nope"), policy)

    def test_orm_object_supported(self, policy, db_session):
        # reconcile should also accept an ORM Shop object (used by seed script).
        from app.models import Shop

        shop = Shop(
            shop_id=99,
            gstin=VALID_GSTIN,
            shop_name="Test",
            shop_category="kirana_without_inventory",
            state_code="27",
            gstin_valid=True,
            upi_turnover=500_000.0,
            gst_turnover=1_000_000.0,
            purchases=900_000.0,  # goods_sold = 900_000; expected = 900_000 / (1 - 0.10) = 1_000_000
            inventory_value=100_000.0,
            cash_sales=500_000.0,
        )
        result = reconcile(shop, policy)
        assert result["verdict"] == "approved"
