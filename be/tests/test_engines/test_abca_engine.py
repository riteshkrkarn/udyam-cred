"""Tests for ABCA engine."""
import pytest
from app.engines.abca_engine import calculate_abca


class TestAbcaEngine:
    """Test ABCA calculation."""

    def test_both_sources_present_agree(self):
        """Test ABCA with both sources present and agreeing within 20%."""
        upi_data = {
            "data": [{"amount": 10000} for _ in range(12)],  # 10000/month
            "vintage_date": "2023-01-01",
        }
        aa_data = {
            "data": [{"deposits": 10500} for _ in range(12)],  # 10500/month
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, aa_data)

        assert result["abca_value"] == pytest.approx(10250.0)  # (10000 + 10500) / 2
        assert result["upi_avg"] == 10000.0
        assert result["aa_avg"] == 10500.0
        assert result["confidence"] == 0.9  # Within 20%
        assert result["vintage_dates"]["upi_vintage"] == "2023-01-01"
        assert result["vintage_dates"]["aa_vintage"] == "2023-01-01"

    def test_both_sources_present_differ(self):
        """Test ABCA with both sources present but differing >20%."""
        upi_data = {
            "data": [{"amount": 10000} for _ in range(12)],
            "vintage_date": "2023-01-01",
        }
        aa_data = {
            "data": [{"deposits": 15000} for _ in range(12)],
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, aa_data)

        assert result["abca_value"] == pytest.approx(12500.0)  # (10000 + 15000) / 2
        assert result["confidence"] == 0.7  # Differs > 20%

    def test_upi_only(self):
        """Test ABCA with only UPI source."""
        upi_data = {
            "data": [{"amount": 8000} for _ in range(12)],
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, None)

        assert result["abca_value"] == 8000.0
        assert result["upi_avg"] == 8000.0
        assert result["aa_avg"] is None
        assert result["confidence"] == 0.6  # Single source

    def test_aa_only(self):
        """Test ABCA with only AA source."""
        aa_data = {
            "data": [{"deposits": 12000} for _ in range(12)],
            "vintage_date": "2023-02-01",
        }

        result = calculate_abca(None, aa_data)

        assert result["abca_value"] == 12000.0
        assert result["upi_avg"] is None
        assert result["aa_avg"] == 12000.0
        assert result["confidence"] == 0.6

    def test_no_sources(self):
        """Test ABCA with no data sources."""
        result = calculate_abca(None, None)

        assert result["abca_value"] == 0.0
        assert result["confidence"] == 0.0

    def test_empty_data(self):
        """Test ABCA with empty data lists."""
        upi_data = {"data": [], "vintage_date": "2023-01-01"}
        aa_data = {"data": [], "vintage_date": "2023-01-01"}

        result = calculate_abca(upi_data, aa_data)

        assert result["abca_value"] == 0.0
        assert result["confidence"] == 0.0

    def test_zero_amounts(self):
        """Test ABCA with zero amounts."""
        upi_data = {"data": [{"amount": 0} for _ in range(12)], "vintage_date": "2023-01-01"}
        aa_data = {"data": [{"deposits": 0} for _ in range(12)], "vintage_date": "2023-01-01"}

        result = calculate_abca(upi_data, aa_data)

        assert result["abca_value"] == 0.0

    def test_negative_amounts_ignored(self):
        """Test that negative amounts are ignored in UPI inflows."""
        upi_data = {
            "data": [{"amount": 10000} for _ in range(6)] + [{"amount": -5000} for _ in range(6)],
            "vintage_date": "2023-01-01",
        }
        aa_data = None

        result = calculate_abca(upi_data, aa_data)

        # Only positive amounts count: 10000 * 6 = 60000, average = 5000
        assert result["upi_avg"] == 5000.0

    def test_high_variance_low_confidence(self):
        """Test that high variance between UPI and AA yields low confidence."""
        upi_data = {
            "data": [{"amount": 5000} for _ in range(12)],
            "vintage_date": "2023-01-01",
        }
        aa_data = {
            "data": [{"deposits": 50000} for _ in range(12)],
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, aa_data)

        # Large difference (10x), should have low confidence
        # Confidence is 0.7 when they differ > 20%
        assert result["confidence"] <= 0.7

    def test_large_data_sample(self):
        """Test ABCA with larger monthly data."""
        upi_data = {
            "data": [{"amount": 100000 + i * 1000} for i in range(12)],
            "vintage_date": "2023-01-01",
        }
        aa_data = {
            "data": [{"deposits": 105000 + i * 1000} for i in range(12)],
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, aa_data)

        assert result["abca_value"] > 0
        assert result["confidence"] > 0

    def test_vintage_date_tracking(self):
        """Test that vintage dates are properly tracked."""
        upi_data = {
            "data": [{"amount": 10000} for _ in range(12)],
            "vintage_date": "2023-03-15",
        }
        aa_data = {
            "data": [{"deposits": 10000} for _ in range(12)],
            "vintage_date": "2023-02-01",
        }

        result = calculate_abca(upi_data, aa_data)

        assert result["vintage_dates"]["upi_vintage"] == "2023-03-15"
        assert result["vintage_dates"]["aa_vintage"] == "2023-02-01"

    def test_very_small_amounts(self):
        """Test ABCA with very small amounts (< 100)."""
        upi_data = {
            "data": [{"amount": 50} for _ in range(12)],
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, None)

        assert result["abca_value"] == 50.0

    def test_mixed_positive_zero_amounts(self):
        """Test ABCA with mixed positive and zero amounts."""
        # The engine averages over all 12 months, including zeros
        # So (10000 + 0 + 10000 + 0*9) / 12 = 20000/12 = 1666.67
        upi_data = {
            "data": [{"amount": 10000}, {"amount": 0}, {"amount": 10000}] + 
                    [{"amount": 0} for _ in range(9)],
            "vintage_date": "2023-01-01",
        }

        result = calculate_abca(upi_data, None)

        # Average over all 12 entries: (10000 + 0 + 10000 + 0*9) / 12
        assert result["upi_avg"] == pytest.approx(1666.67, rel=0.01)
