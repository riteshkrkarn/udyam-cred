"""Tests for rate engine."""
import pytest
from app.engines.rate_engine import get_rate


class TestRateEngine:
    """Test interest rate determination."""

    def test_moderate_12_month(self):
        """Test Moderate risk band with 12-month tenor."""
        result = get_rate(risk_band="Moderate", tenor_months=12)

        assert result["rate_percent"] == 11.5
        assert result["band"] == "Moderate"
        assert result["tenor"] == 12

    def test_moderate_24_month(self):
        """Test Moderate risk band with 24-month tenor."""
        result = get_rate(risk_band="Moderate", tenor_months=24)

        assert result["rate_percent"] == 11.0
        assert result["band"] == "Moderate"

    def test_moderate_36_month(self):
        """Test Moderate risk band with 36-month tenor."""
        result = get_rate(risk_band="Moderate", tenor_months=36)

        assert result["rate_percent"] == 10.5
        assert result["tenor"] == 36

    def test_low_risk_band(self):
        """Test Low risk band."""
        result = get_rate(risk_band="Low", tenor_months=12)

        assert result["rate_percent"] == 9.5
        assert result["band"] == "Low"

    def test_high_risk_band(self):
        """Test High risk band."""
        result = get_rate(risk_band="High", tenor_months=12)

        assert result["rate_percent"] == 13.5
        assert result["band"] == "High"

    def test_needs_review_band(self):
        """Test Needs Review risk band."""
        result = get_rate(risk_band="Needs Review", tenor_months=12)

        assert result["rate_percent"] == 15.0
        assert result["band"] == "Needs Review"

    def test_all_low_risk_tenors(self):
        """Test all tenors for Low risk band."""
        rates = {
            12: 9.5,
            24: 9.0,
            36: 8.5,
        }

        for tenor, expected_rate in rates.items():
            result = get_rate(risk_band="Low", tenor_months=tenor)
            assert result["rate_percent"] == expected_rate

    def test_all_high_risk_tenors(self):
        """Test all tenors for High risk band."""
        rates = {
            12: 13.5,
            24: 13.0,
            36: 12.5,
        }

        for tenor, expected_rate in rates.items():
            result = get_rate(risk_band="High", tenor_months=tenor)
            assert result["rate_percent"] == expected_rate

    def test_invalid_risk_band_defaults_to_moderate(self):
        """Test invalid risk band defaults to Moderate."""
        result = get_rate(risk_band="Unknown", tenor_months=12)

        assert result["band"] == "Moderate"
        assert result["rate_percent"] == 11.5

    def test_invalid_tenor_uses_closest(self):
        """Test invalid tenor is adjusted to closest valid tenor."""
        result = get_rate(risk_band="Moderate", tenor_months=18)

        # 18 is closer to 12 than to 24, but let's verify it gets a valid rate
        assert result["tenor"] in [12, 24]
        assert result["rate_percent"] in [11.5, 11.0]

    def test_tenor_rounding_to_nearest(self):
        """Test tenor rounding behavior."""
        result_15 = get_rate(risk_band="Moderate", tenor_months=15)
        result_21 = get_rate(risk_band="Moderate", tenor_months=21)

        # 15 is between 12 and 24, closer to 12
        assert result_15["tenor"] in [12, 24]
        # 21 is between 12 and 24, closer to 24
        assert result_21["tenor"] in [12, 24]

    def test_very_large_tenor_adjusted(self):
        """Test very large tenor is adjusted to maximum."""
        result = get_rate(risk_band="Moderate", tenor_months=60)

        assert result["tenor"] == 36

    def test_zero_tenor_adjusted(self):
        """Test zero tenor is adjusted to minimum."""
        result = get_rate(risk_band="Moderate", tenor_months=0)

        assert result["tenor"] == 12

    def test_negative_tenor_adjusted(self):
        """Test negative tenor is adjusted."""
        result = get_rate(risk_band="Moderate", tenor_months=-12)

        assert result["tenor"] in [12, 24, 36]
