"""Tests for capacity engine."""
import pytest
from app.engines.capacity_engine import get_safe_amount, _fallback_safe_amount


class TestCapacityEngine:
    """Test capacity model and fallback logic."""

    def test_fallback_with_abca_present(self):
        """Test fallback rule with ABCA available."""
        result = get_safe_amount(
            goods_sold=100000,
            margin=20,
            family_size=4,
            liabilities=50000,
            round_trip_score=0.0,
            vintage_months=12,
            abca=50000,
        )

        # fallback: 50000 * 0.5 * (1 - 0 * 0.3) = 25000
        assert result["safe_amount"] == pytest.approx(25000, rel=0.01)
        assert result["confidence"] == 0.6

    def test_fallback_with_round_trip_penalty(self):
        """Test fallback with round-trip risk penalty."""
        result = get_safe_amount(
            goods_sold=100000,
            margin=20,
            family_size=4,
            liabilities=50000,
            round_trip_score=0.5,
            vintage_months=12,
            abca=50000,
        )

        # fallback: 50000 * 0.5 * (1 - 0.5 * 0.3) = 50000 * 0.5 * 0.85 = 21250
        assert result["safe_amount"] == pytest.approx(21250, rel=0.01)
        assert result["confidence"] == 0.6

    def test_fallback_estimate_abca_from_goods_sold(self):
        """Test fallback estimating ABCA from goods_sold when ABCA missing."""
        # margin=20 means cost = selling_price / (1 - 0.2) = selling_price / 0.8
        # If goods_sold = 100000, estimated_abca = 100000 / (1 - 0.2) * 0.6 = 100000 / 0.8 * 0.6 = 75000
        result = get_safe_amount(
            goods_sold=100000,
            margin=20,
            family_size=4,
            liabilities=50000,
            round_trip_score=0.0,
            vintage_months=12,
            abca=None,
        )

        # 75000 * 0.5 * 1.0 = 37500
        assert result["safe_amount"] == pytest.approx(37500, rel=0.01)
        assert result["confidence"] == 0.6

    def test_zero_goods_sold_fallback(self):
        """Test fallback with zero goods sold."""
        result = get_safe_amount(
            goods_sold=0,
            margin=20,
            family_size=4,
            liabilities=50000,
            round_trip_score=0.0,
            vintage_months=12,
            abca=None,
        )

        assert result["safe_amount"] == 0.0
        assert result["confidence"] == 0.6

    def test_high_round_trip_score_reduces_amount(self):
        """Test that high round-trip score significantly reduces safe amount."""
        result_clean = get_safe_amount(
            goods_sold=100000,
            margin=20,
            family_size=4,
            liabilities=0,
            round_trip_score=0.0,
            vintage_months=12,
            abca=50000,
        )

        result_risky = get_safe_amount(
            goods_sold=100000,
            margin=20,
            family_size=4,
            liabilities=0,
            round_trip_score=1.0,
            vintage_months=12,
            abca=50000,
        )

        # High round-trip score (1.0) reduces: 1 - 1.0 * 0.3 = 0.7
        assert result_risky["safe_amount"] < result_clean["safe_amount"]

    def test_safe_amount_bounded_at_policy_cap(self):
        """Test that safe amount is bounded at 500,000."""
        result = get_safe_amount(
            goods_sold=10000000,
            margin=50,
            family_size=4,
            liabilities=0,
            round_trip_score=0.0,
            vintage_months=12,
            abca=2000000,
        )

        # With such high ABCA, amount would exceed cap
        assert result["safe_amount"] <= 500000

    def test_safe_amount_non_negative(self):
        """Test that safe amount is never negative."""
        result = get_safe_amount(
            goods_sold=0,
            margin=0,
            family_size=1,
            liabilities=0,
            round_trip_score=1.0,
            vintage_months=0,
            abca=0,
        )

        assert result["safe_amount"] >= 0.0


class TestFallbackSafeAmount:
    """Test fallback rule directly."""

    def test_fallback_with_abca(self):
        """Test fallback calculation with ABCA."""
        amount = _fallback_safe_amount(
            abca=100000, goods_sold=0, margin=0, round_trip_score=0.0
        )

        assert amount == pytest.approx(50000, rel=0.01)

    def test_fallback_without_abca_with_goods_sold(self):
        """Test fallback estimating ABCA from goods sold."""
        # goods_sold=50000, margin=10 -> estimated_abca = 50000 / (1 - 0.1) * 0.6 = 50000 / 0.9 * 0.6 = 33333.33
        # safe_amount = 33333.33 * 0.5 = 16666.67
        amount = _fallback_safe_amount(
            abca=None, goods_sold=50000, margin=10, round_trip_score=0.0
        )

        assert amount == pytest.approx(16666.67, rel=0.01)

    def test_fallback_round_trip_penalty(self):
        """Test fallback applies round-trip penalty."""
        # Without penalty: 100000 * 0.5 = 50000
        # With penalty (score=0.5): 100000 * 0.5 * (1 - 0.5*0.3) = 100000 * 0.5 * 0.85 = 42500
        amount = _fallback_safe_amount(
            abca=100000, goods_sold=0, margin=0, round_trip_score=0.5
        )

        assert amount == pytest.approx(42500, rel=0.01)
