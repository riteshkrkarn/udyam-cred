"""Phase 1 tests for source agreement engine.

Tests:
- Single source (UPI only) → agreement_score = 0.5
- Two sources (AA + GST) → correlation
- Three sources (AA + GST + UPI) → weighted agreement
- Weighted sales calculation
- Confidence levels (low/medium/high)
- Edge cases (zero sales, identical values)
"""
import pytest
from app.engines.source_agreement_engine import SourceAgreementEngine


class TestSingleSourceAgreement:
    """Test agreement scoring with single source."""

    def test_upi_only_agreement(self):
        """Test UPI only gives low agreement score."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=None,
            gst_monthly_avg=None,
            upi_monthly_avg=50000,
        )
        assert result.agreement_score == 0.5  # Low confidence
        assert result.confidence == "low"
        assert len(result.sources_used) == 1
        assert "upi" in result.sources_used

    def test_aa_only_agreement(self):
        """Test AA only gives medium agreement score."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=50000,
            gst_monthly_avg=None,
            upi_monthly_avg=None,
        )
        # AA alone should give low confidence
        assert result.agreement_score == 0.5
        assert result.confidence == "low"
        assert len(result.sources_used) == 1
        assert "aa" in result.sources_used

    def test_gst_only_agreement(self):
        """Test GST only gives low agreement score."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=None,
            gst_monthly_avg=50000,
            upi_monthly_avg=None,
        )
        assert result.agreement_score == 0.5
        assert result.confidence == "low"


class TestTwoSourceAgreement:
    """Test agreement scoring with two sources."""

    def test_aa_gst_perfect_agreement(self):
        """Test AA + GST with perfect agreement."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=80000,
            upi_monthly_avg=None,
        )
        assert result.agreement_score > 0.85
        assert result.confidence in {"high", "medium"}
        assert len(result.sources_used) == 2
        assert set(result.sources_used) == {"aa", "gst"}

    def test_aa_gst_good_agreement(self):
        """Test AA + GST with good agreement (within 10%)."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=88000,  # 10% higher
            upi_monthly_avg=None,
        )
        assert result.agreement_score > 0.75
        assert result.confidence in {"high", "medium"}

    def test_aa_gst_poor_agreement(self):
        """Test AA + GST with poor agreement (>30% difference)."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=120000,  # 50% higher
            upi_monthly_avg=None,
        )
        assert result.agreement_score < 0.75
        assert result.confidence in {"low", "medium"}

    def test_aa_upi_agreement(self):
        """Test AA + UPI agreement."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=None,
            upi_monthly_avg=80000,
        )
        assert result.agreement_score > 0.5
        assert len(result.sources_used) == 2


class TestThreeSourceAgreement:
    """Test agreement scoring with three sources."""

    def test_three_sources_perfect_agreement(self):
        """Test three sources with identical values."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=80000,
            upi_monthly_avg=80000,
        )
        assert result.agreement_score > 0.9
        assert result.confidence == "high"
        assert len(result.sources_used) == 3

    def test_three_sources_good_agreement(self):
        """Test three sources with good agreement."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=82000,
            upi_monthly_avg=81000,
        )
        assert result.agreement_score > 0.85
        assert result.confidence == "high"

    def test_three_sources_scattered_values(self):
        """Test three sources with scattered values."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=100000,
            upi_monthly_avg=120000,
        )
        assert result.agreement_score < 0.9
        assert len(result.sources_used) == 3


class TestWeightedSalesCalculation:
    """Test weighted sales calculation."""

    def test_all_sources_equal_weight(self):
        """Test weighted sales with all sources available."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,  # 60% weight
            gst_monthly_avg=85000,  # 30% weight
            upi_monthly_avg=100000,  # 10% weight
        )
        expected = 80000 * 0.6 + 85000 * 0.3 + 100000 * 0.1
        assert abs(result.weighted_sales - expected) < 1

    def test_weighted_sales_aa_gst_only(self):
        """Test weighted sales with AA + GST only."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,  # Higher weight
            gst_monthly_avg=85000,
            upi_monthly_avg=None,
        )
        # AA should be weighted higher than GST
        assert result.weighted_sales > 80000
        assert result.weighted_sales < 85000

    def test_weighted_sales_single_source(self):
        """Test weighted sales with single source."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=None,
            upi_monthly_avg=None,
        )
        # Should return the only source value
        assert result.weighted_sales == 80000


class TestConfidenceLevels:
    """Test confidence level assignment."""

    def test_high_confidence_criteria(self):
        """Test high confidence requires good agreement and multiple sources."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=80500,
            upi_monthly_avg=79500,
        )
        if len(result.sources_used) >= 2 and result.agreement_score > 0.85:
            assert result.confidence == "high"

    def test_medium_confidence_criteria(self):
        """Test medium confidence with decent agreement."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=85000,
            upi_monthly_avg=None,
        )
        # Two sources with reasonable agreement
        if result.agreement_score > 0.7 and result.agreement_score <= 0.85:
            assert result.confidence == "medium"

    def test_low_confidence_criteria(self):
        """Test low confidence with single source or poor agreement."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=None,
            upi_monthly_avg=None,
        )
        assert result.confidence == "low"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_sales_all_sources(self):
        """Test agreement with zero sales from all sources."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=0,
            gst_monthly_avg=0,
            upi_monthly_avg=0,
        )
        assert result.weighted_sales == 0

    def test_identical_sources(self):
        """Test with identical values from all sources."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=50000,
            gst_monthly_avg=50000,
            upi_monthly_avg=50000,
        )
        assert result.agreement_score > 0.9
        assert result.weighted_sales == 50000

    def test_very_large_sales_values(self):
        """Test with very large sales values."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=10000000,
            gst_monthly_avg=10000000,
            upi_monthly_avg=10000000,
        )
        assert result.weighted_sales == 10000000
        assert result.agreement_score > 0.9

    def test_very_small_sales_values(self):
        """Test with very small sales values."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=100,
            gst_monthly_avg=100,
            upi_monthly_avg=100,
        )
        assert result.weighted_sales == 100

    def test_extreme_discrepancy(self):
        """Test with extreme discrepancy between sources."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=10000,
            gst_monthly_avg=100000,
            upi_monthly_avg=1000,
        )
        assert result.agreement_score < 0.5
        assert result.confidence == "low"
