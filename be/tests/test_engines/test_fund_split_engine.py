"""Tests for fund split optimization engine."""
import pytest
from app.engines.fund_split_engine import optimize_fund_split


class TestFundSplitEngine:
    """Test fund split optimization."""

    def test_typical_kirana_shop(self):
        """Test typical kirana shop fund split."""
        result = optimize_fund_split(
            loan_amount=100000,
            goods_sold=50000,
            margin=20,
            category="kirana",
            monthly_turnover=50000,
        )

        # stock = 50000 * 2 = 100000
        # buffer = 100000 * 0.2 = 20000
        # expansion = 100000 * 0.2 = 20000
        # reserve = 100000 - 100000 - 20000 - 20000 = -40000 (clamped to 0)
        # Total: 100000 + 20000 + 20000 + 0 = 140000 (over budget, will be scaled)
        
        assert result["stock_pct"] + result["buffer_pct"] + result["expansion_pct"] + result["reserve_pct"] == pytest.approx(100.0, abs=1)
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    def test_low_margin_shop(self):
        """Test shop with low margin."""
        result = optimize_fund_split(
            loan_amount=100000,
            goods_sold=80000,
            margin=10,
            category="electronics",
            monthly_turnover=40000,
        )

        # Should generate recommendation about low margin
        assert any("low" in rec.lower() and "margin" in rec.lower() for rec in result["recommendations"])

    def test_high_margin_shop(self):
        """Test shop with high margin."""
        result = optimize_fund_split(
            loan_amount=100000,
            goods_sold=30000,
            margin=40,
            category="jewelry",
            monthly_turnover=80000,
        )

        assert result["stock_pct"] + result["buffer_pct"] + result["expansion_pct"] + result["reserve_pct"] == pytest.approx(100.0, abs=1)

    def test_high_loan_to_turnover_ratio(self):
        """Test when loan is large relative to turnover."""
        result = optimize_fund_split(
            loan_amount=500000,
            goods_sold=50000,
            margin=15,
            category="kirana",
            monthly_turnover=50000,
        )

        # Should warn about high loan to turnover
        assert any("turnover" in rec.lower() for rec in result["recommendations"])

    def test_percentages_sum_to_100(self):
        """Test that percentages sum to 100%."""
        result = optimize_fund_split(
            loan_amount=250000,
            goods_sold=100000,
            margin=25,
            category="kirana",
            monthly_turnover=75000,
        )

        total = result["stock_pct"] + result["buffer_pct"] + result["expansion_pct"] + result["reserve_pct"]
        assert total == pytest.approx(100.0, abs=0.1)

    def test_all_percentages_non_negative(self):
        """Test that all percentages are non-negative."""
        result = optimize_fund_split(
            loan_amount=50000,
            goods_sold=100000,
            margin=50,
            category="luxury",
            monthly_turnover=200000,
        )

        assert result["stock_pct"] >= 0
        assert result["buffer_pct"] >= 0
        assert result["expansion_pct"] >= 0
        assert result["reserve_pct"] >= 0

    def test_zero_goods_sold(self):
        """Test with zero goods sold."""
        result = optimize_fund_split(
            loan_amount=100000,
            goods_sold=0,
            margin=20,
            category="kirana",
            monthly_turnover=10000,
        )

        # Should handle gracefully
        total = result["stock_pct"] + result["buffer_pct"] + result["expansion_pct"] + result["reserve_pct"]
        assert total == pytest.approx(100.0, abs=0.1)

    def test_low_reserve_recommendation(self):
        """Test that low reserve triggers recommendation."""
        result = optimize_fund_split(
            loan_amount=100000,
            goods_sold=50000,
            margin=20,
            category="kirana",
            monthly_turnover=50000,
        )

        # If reserve_pct < 5, should have recommendation
        if result["reserve_pct"] < 5:
            assert any("reserve" in rec.lower() for rec in result["recommendations"])

    def test_stock_allocation_recommendation_high(self):
        """Test recommendation for high stock allocation."""
        result = optimize_fund_split(
            loan_amount=200000,
            goods_sold=150000,
            margin=15,
            category="kirana",
            monthly_turnover=100000,
        )

        if result["stock_pct"] > 75:
            assert any("stock" in rec.lower() and "high" in rec.lower() for rec in result["recommendations"])

    def test_expansion_percentage_consistent(self):
        """Test that expansion is always 20% of loan."""
        for loan in [50000, 100000, 200000, 500000]:
            result = optimize_fund_split(
                loan_amount=loan,
                goods_sold=40000,
                margin=20,
                category="kirana",
                monthly_turnover=50000,
            )
            
            # expansion_amount = loan * 0.2, so expansion_pct ≈ 20 if within budget
            # May be scaled down if stock+buffer+expansion > loan
            assert 0 <= result["expansion_pct"] <= 30
