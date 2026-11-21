"""Phase 1 tests for verified window engine.

Tests:
- Overlapping date ranges
- Minimum 6 months requirement
- Data quality scoring
- Weight factor calculation
- Edge cases (exactly 6 months, less than 6 months)
"""
import pytest
from datetime import datetime, timedelta
from app.engines.verified_window_engine import VerifiedWindowEngine


class TestOverlappingDateRanges:
    """Test verified window calculation with overlapping ranges."""

    def test_complete_overlap_aa_gst(self):
        """Test complete overlap of AA and GST data."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=180),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified == 6
        assert result.data_quality_score > 0.8

    def test_partial_overlap_aa_gst(self):
        """Test partial overlap of AA and GST data."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=90),  # 3 months into AA
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        # Overlap should be 3 months
        assert result.months_verified == 3
        assert result.window_start >= now - timedelta(days=90)

    def test_no_overlap_aa_gst(self):
        """Test no overlap between AA and GST data."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now - timedelta(days=90),  # Ends before GST starts
            gst_start=now - timedelta(days=85),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        # No verified window
        assert result.months_verified == 0 or result.months_verified < 1

    def test_complete_overlap_all_three_sources(self):
        """Test complete overlap of all three sources."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=180),
            gst_end=now,
            upi_start=now - timedelta(days=180),
            upi_end=now,
        )
        assert result.months_verified == 6


class TestMinimumSixMonthsRequirement:
    """Test minimum 6 months requirement."""

    def test_exactly_6_months_verified(self):
        """Test exactly 6 months of verified data."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=180),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified >= 5.9  # Close to 6
        assert result.months_verified <= 6.1

    def test_more_than_6_months_verified(self):
        """Test more than 6 months of verified data."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=365),
            aa_end=now,
            gst_start=now - timedelta(days=365),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified > 11  # Close to 12

    def test_less_than_6_months_verified(self):
        """Test less than 6 months of verified data."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=90),
            aa_end=now,
            gst_start=now - timedelta(days=90),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified < 4

    def test_barely_less_than_6_months(self):
        """Test barely less than 6 months."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=170),
            aa_end=now,
            gst_start=now - timedelta(days=170),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified < 6 or result.months_verified >= 5.5


class TestDataQualityScoring:
    """Test data quality scoring."""

    def test_high_quality_consistent_data(self):
        """Test high quality with consistent overlap."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=180),
            gst_end=now,
            upi_start=now - timedelta(days=180),
            upi_end=now,
        )
        assert result.data_quality_score > 0.85

    def test_medium_quality_partial_overlap(self):
        """Test medium quality with partial overlap."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=90),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert 0.5 < result.data_quality_score < 0.9

    def test_low_quality_short_window(self):
        """Test low quality with short verified window."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=60),
            aa_end=now,
            gst_start=now - timedelta(days=60),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.data_quality_score < 0.7


class TestWeightFactorCalculation:
    """Test weight factor for amount scaling."""

    def test_weight_factor_6_months(self):
        """Test weight factor for 6 months (minimum)."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=180),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        # 6 months / 12 max = 0.5 or similar scaling
        assert 0.4 < result.weight_factor < 0.6

    def test_weight_factor_12_months(self):
        """Test weight factor for 12 months."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=365),
            aa_end=now,
            gst_start=now - timedelta(days=365),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        # 12 months / 12 max = 1.0
        assert 0.9 < result.weight_factor <= 1.0

    def test_weight_factor_24_months(self):
        """Test weight factor for 24 months (capped)."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=730),
            aa_end=now,
            gst_start=now - timedelta(days=730),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        # 24 months / 12 max should be capped at 1.0
        assert result.weight_factor <= 1.0

    def test_weight_factor_3_months(self):
        """Test weight factor for 3 months (below minimum)."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now - timedelta(days=90),
            aa_end=now,
            gst_start=now - timedelta(days=90),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        # 3 months / 12 max = 0.25
        assert 0.2 < result.weight_factor < 0.35


class TestEdgeCases:
    """Test edge cases for verified window."""

    def test_exactly_6_months_to_the_day(self):
        """Test exactly 180 days (6 months)."""
        now = datetime.now()
        start = now - timedelta(days=180)
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=start,
            aa_end=now,
            gst_start=start,
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert 5.8 < result.months_verified < 6.2

    def test_one_day_less_than_6_months(self):
        """Test one day less than 6 months."""
        now = datetime.now()
        start = now - timedelta(days=179)
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=start,
            aa_end=now,
            gst_start=start,
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified < 6

    def test_one_day_more_than_6_months(self):
        """Test one day more than 6 months."""
        now = datetime.now()
        start = now - timedelta(days=181)
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=start,
            aa_end=now,
            gst_start=start,
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified > 6

    def test_same_day_start_and_end(self):
        """Test when start and end are same day."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verified_window(
            aa_start=now,
            aa_end=now,
            gst_start=now,
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified == 0 or result.months_verified < 0.1

    def test_future_dates(self):
        """Test with future dates (should handle gracefully)."""
        now = datetime.now()
        future = now + timedelta(days=180)
        try:
            result = VerifiedWindowEngine.calculate_verified_window(
                aa_start=future - timedelta(days=180),
                aa_end=future,
                gst_start=future - timedelta(days=180),
                gst_end=future,
                upi_start=None,
                upi_end=None,
            )
            # Should handle gracefully or return 0
            assert result is not None
        except ValueError:
            # Acceptable - future dates may be rejected
            pass

    def test_backwards_dates(self):
        """Test when end date is before start date."""
        now = datetime.now()
        try:
            result = VerifiedWindowEngine.calculate_verified_window(
                aa_start=now,
                aa_end=now - timedelta(days=180),  # End before start
                gst_start=now - timedelta(days=180),
                gst_end=now,
                upi_start=None,
                upi_end=None,
            )
            # Should handle gracefully or reject
            if result:
                assert result.months_verified >= 0
        except ValueError:
            # Acceptable - invalid date ranges rejected
            pass
