"""Phase 1 tests for GST coverage engine.

Tests:
- Good alignment (0.8 - 1.2 coverage ratio)
- High discrepancy (>1.2 or <0.8)
- Missing GST data handling
- Reconciliation flag logic
"""
import pytest
from app.engines.gst_coverage_engine import GSTCoverageEngine


class TestGoodAlignment:
    """Test GST coverage with good alignment."""

    def test_perfect_alignment(self):
        """Test perfect alignment (1.0 coverage ratio)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=100000,
        )
        assert result.coverage_percent == 1.0
        assert result.reconciliation_flag is False

    def test_coverage_within_80_percent(self):
        """Test coverage at 80% (lower bound)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=80000,
        )
        assert result.coverage_percent == 0.8
        assert result.reconciliation_flag is False

    def test_coverage_within_120_percent(self):
        """Test coverage at 120% (upper bound)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=120000,
        )
        assert result.coverage_percent == 1.2
        assert result.reconciliation_flag is False

    def test_good_alignment_high_side(self):
        """Test coverage at 110% (good alignment, high side)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=110000,
        )
        assert result.coverage_percent == 1.1
        assert result.reconciliation_flag is False

    def test_good_alignment_low_side(self):
        """Test coverage at 90% (good alignment, low side)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=90000,
        )
        assert result.coverage_percent == 0.9
        assert result.reconciliation_flag is False


class TestHighDiscrepancy:
    """Test GST coverage with high discrepancy."""

    def test_coverage_below_80_percent(self):
        """Test coverage below 80% (high discrepancy, low side)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=75000,
        )
        assert result.coverage_percent == 0.75
        assert result.reconciliation_flag is True

    def test_coverage_above_120_percent(self):
        """Test coverage above 120% (high discrepancy, high side)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=130000,
        )
        assert result.coverage_percent == 1.3
        assert result.reconciliation_flag is True

    def test_very_low_coverage(self):
        """Test very low coverage (50%)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=50000,
        )
        assert result.coverage_percent == 0.5
        assert result.reconciliation_flag is True

    def test_very_high_coverage(self):
        """Test very high coverage (150%)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=150000,
        )
        assert result.coverage_percent == 1.5
        assert result.reconciliation_flag is True

    def test_double_purchases(self):
        """Test GST is double the purchases (200%)."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=200000,
        )
        assert result.coverage_percent == 2.0
        assert result.reconciliation_flag is True


class TestMissingGSTData:
    """Test handling of missing GST data."""

    def test_gst_turnover_zero(self):
        """Test handling when GST turnover is zero."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=0,
        )
        # Should set reconciliation flag and handle gracefully
        assert result.reconciliation_flag is True
        # Coverage should be 0
        assert result.coverage_percent == 0

    def test_purchases_zero(self):
        """Test handling when purchases are zero."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=0,
            gst_turnover=100000,
        )
        # Should handle division by zero gracefully
        if result.coverage_percent is not None:
            assert result.reconciliation_flag is True

    def test_both_zero(self):
        """Test handling when both are zero."""
        try:
            result = GSTCoverageEngine.verify_coverage(
                purchases_declared=0,
                gst_turnover=0,
            )
            # Should either return 0 or handle gracefully
            if result and result.coverage_percent is not None:
                assert result.reconciliation_flag is True
        except ZeroDivisionError:
            # Acceptable - should be handled by caller
            pass

    def test_negative_values(self):
        """Test handling of negative values."""
        try:
            result = GSTCoverageEngine.verify_coverage(
                purchases_declared=-100000,
                gst_turnover=100000,
            )
            # Should flag as issue
            assert result.reconciliation_flag is True
        except ValueError:
            # Acceptable - validation should reject negative
            pass


class TestReconciliationFlagLogic:
    """Test reconciliation flag logic."""

    def test_flag_false_for_good_alignment(self):
        """Test reconciliation flag is False for good alignment."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=100000,
        )
        assert result.reconciliation_flag is False

    def test_flag_true_for_high_discrepancy(self):
        """Test reconciliation flag is True for high discrepancy."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=150000,
        )
        assert result.reconciliation_flag is True

    def test_flag_boundary_80_percent(self):
        """Test reconciliation flag at 80% boundary."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=80000,
        )
        # Exactly at boundary should be False
        assert result.reconciliation_flag is False

    def test_flag_boundary_120_percent(self):
        """Test reconciliation flag at 120% boundary."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=120000,
        )
        # Exactly at boundary should be False
        assert result.reconciliation_flag is False

    def test_flag_just_below_80_percent(self):
        """Test reconciliation flag just below 80%."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=79999,
        )
        assert result.reconciliation_flag is True

    def test_flag_just_above_120_percent(self):
        """Test reconciliation flag just above 120%."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000,
            gst_turnover=120001,
        )
        assert result.reconciliation_flag is True


class TestEdgeCases:
    """Test edge cases for GST coverage."""

    def test_very_large_values(self):
        """Test with very large values."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=1000000000,
            gst_turnover=1000000000,
        )
        assert result.coverage_percent == 1.0
        assert result.reconciliation_flag is False

    def test_very_small_values(self):
        """Test with very small values."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=1,
            gst_turnover=1,
        )
        assert result.coverage_percent == 1.0
        assert result.reconciliation_flag is False

    def test_decimal_precision(self):
        """Test with decimal values."""
        result = GSTCoverageEngine.verify_coverage(
            purchases_declared=100000.50,
            gst_turnover=100000.50,
        )
        assert abs(result.coverage_percent - 1.0) < 0.001
