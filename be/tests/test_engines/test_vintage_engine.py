"""Tests for vintage engine."""
import pytest
from datetime import datetime
from app.engines.vintage_engine import get_vintage


class TestVintageEngine:
    """Test vintage date determination."""

    def test_both_same_dates(self):
        """Test with both sources having same vintage date."""
        result = get_vintage("2023-01-01", "2023-01-01")

        assert result["earliest_date"] == "2023-01-01T00:00:00"
        assert result["supporting_sources_count"] == 2

    def test_upi_older(self):
        """Test with UPI older than AA."""
        result = get_vintage("2022-01-01", "2023-01-01")

        assert result["earliest_date"] == "2022-01-01T00:00:00"
        assert result["supporting_sources_count"] == 2

    def test_aa_older(self):
        """Test with AA older than UPI."""
        result = get_vintage("2023-06-01", "2023-01-01")

        assert result["earliest_date"] == "2023-01-01T00:00:00"
        assert result["supporting_sources_count"] == 2

    def test_upi_only(self):
        """Test with only UPI vintage."""
        result = get_vintage("2023-01-15", None)

        assert result["earliest_date"] == "2023-01-15T00:00:00"
        assert result["supporting_sources_count"] == 1

    def test_aa_only(self):
        """Test with only AA vintage."""
        result = get_vintage(None, "2023-03-01")

        assert result["earliest_date"] == "2023-03-01T00:00:00"
        assert result["supporting_sources_count"] == 1

    def test_no_dates(self):
        """Test with no vintage dates."""
        result = get_vintage(None, None)

        assert result["earliest_date"] is None
        assert result["supporting_sources_count"] == 0

    def test_invalid_dates(self):
        """Test with invalid date formats."""
        result = get_vintage("invalid", "also-invalid")

        assert result["earliest_date"] is None
        assert result["supporting_sources_count"] == 0

    def test_mixed_valid_invalid(self):
        """Test with one valid and one invalid date."""
        result = get_vintage("2023-01-01", "invalid")

        assert result["earliest_date"] == "2023-01-01T00:00:00"
        assert result["supporting_sources_count"] == 1

    def test_datetime_objects(self):
        """Test with datetime objects instead of strings."""
        upi_date = datetime(2023, 1, 1)
        aa_date = datetime(2023, 2, 1)

        result = get_vintage(upi_date, aa_date)

        assert result["earliest_date"] == "2023-01-01T00:00:00"
        assert result["supporting_sources_count"] == 2
