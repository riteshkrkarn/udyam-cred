"""Test suite for external data adapters (UPI, Account Aggregator, GST)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.adapters.upi_adapter import UPIAdapter
from app.adapters.account_aggregator_adapter import AccountAggregatorAdapter
from app.adapters.gst_adapter import GSTAdapter


class TestUPIAdapter:
    """Tests for UPI data adapter."""

    def test_upi_fetch_test_shop_1(self):
        """Test deterministic UPI data for shop_id=1."""
        adapter = UPIAdapter()
        data = adapter.fetch("1")

        assert data is not None
        assert "vintage_date" in data
        assert "data_hash" in data
        assert "transactions" in data

        # Verify schema
        assert isinstance(data["vintage_date"], datetime)
        assert isinstance(data["data_hash"], str)
        assert isinstance(data["transactions"], list)
        assert len(data["transactions"]) > 0

        # Verify transaction structure
        tx = data["transactions"][0]
        assert "date" in tx
        assert "utr" in tx
        assert "amount" in tx
        assert "counterparty" in tx

    def test_upi_fetch_test_shop_2(self):
        """Test deterministic UPI data for shop_id=2."""
        adapter = UPIAdapter()
        data = adapter.fetch("2")

        assert data is not None
        assert len(data["transactions"]) > 0

    def test_upi_deterministic_same_shop(self):
        """Test that same shop_id returns identical data."""
        adapter = UPIAdapter()
        data1 = adapter.fetch("1")
        data2 = adapter.fetch("1")

        # Should have same hash (content)
        assert data1["data_hash"] == data2["data_hash"]
        assert len(data1["transactions"]) == len(data2["transactions"])

    def test_upi_different_shops_different_data(self):
        """Test that different shops return different data."""
        adapter = UPIAdapter()
        data1 = adapter.fetch("1")
        data2 = adapter.fetch("2")

        # Should have different hashes
        assert data1["data_hash"] != data2["data_hash"]

    def test_upi_random_shop(self):
        """Test deterministic data for arbitrary shop_id."""
        adapter = UPIAdapter()
        data = adapter.fetch("999")

        assert data is not None
        assert len(data["transactions"]) > 0
        assert data["data_hash"]

    def test_upi_invalid_shop_id(self):
        """Test error handling for invalid shop_id."""
        adapter = UPIAdapter()

        with pytest.raises(ValueError):
            adapter.fetch("invalid")

        with pytest.raises(ValueError):
            adapter.fetch("-1")

        with pytest.raises(ValueError):
            adapter.fetch("0")

    def test_upi_12_months_data(self):
        """Test that UPI data covers 12 months."""
        adapter = UPIAdapter()
        data = adapter.fetch("1")
        transactions = data["transactions"]

        # Extract dates
        dates = [tx["date"] for tx in transactions]
        first_date = min(dates)
        last_date = max(dates)

        # Should span roughly 365 days
        from datetime import datetime as dt

        d1 = dt.fromisoformat(first_date).date()
        d2 = dt.fromisoformat(last_date).date()
        diff_days = (d2 - d1).days

        assert diff_days >= 360  # Allow 1 week tolerance

    def test_upi_positive_amounts(self):
        """Test that all UPI amounts are positive."""
        adapter = UPIAdapter()
        data = adapter.fetch("1")

        for tx in data["transactions"]:
            assert tx["amount"] > 0


class TestAccountAggregatorAdapter:
    """Tests for Account Aggregator data adapter."""

    def test_aa_fetch_test_shop_1(self):
        """Test deterministic AA data for shop_id=1."""
        adapter = AccountAggregatorAdapter()
        data = adapter.fetch("1")

        assert data is not None
        assert "vintage_date" in data
        assert "data_hash" in data
        assert "summary" in data

        # Verify schema
        assert isinstance(data["vintage_date"], datetime)
        assert isinstance(data["data_hash"], str)
        assert isinstance(data["summary"], list)
        assert len(data["summary"]) > 0

        # Verify summary structure
        row = data["summary"][0]
        assert "month" in row
        assert "opening_balance" in row
        assert "closing_balance" in row
        assert "total_deposits" in row
        assert "total_withdrawals" in row
        assert "turnover" in row

    def test_aa_deterministic_same_shop(self):
        """Test that same shop_id returns identical data."""
        adapter = AccountAggregatorAdapter()
        data1 = adapter.fetch("1")
        data2 = adapter.fetch("1")

        # Should have same hash
        assert data1["data_hash"] == data2["data_hash"]
        assert len(data1["summary"]) == len(data2["summary"])

    def test_aa_different_shops_different_data(self):
        """Test that different shops return different data."""
        adapter = AccountAggregatorAdapter()
        data1 = adapter.fetch("1")
        data2 = adapter.fetch("2")

        # Should have different hashes
        assert data1["data_hash"] != data2["data_hash"]

    def test_aa_invalid_shop_id(self):
        """Test error handling for invalid shop_id."""
        adapter = AccountAggregatorAdapter()

        with pytest.raises(ValueError):
            adapter.fetch("invalid")

        with pytest.raises(ValueError):
            adapter.fetch("-1")

    def test_aa_positive_balances(self):
        """Test that balances are non-negative."""
        adapter = AccountAggregatorAdapter()
        data = adapter.fetch("1")

        for row in data["summary"]:
            assert row["opening_balance"] >= 0
            assert row["closing_balance"] >= 0
            assert row["total_deposits"] >= 0
            assert row["total_withdrawals"] >= 0

    def test_aa_12_months_data(self):
        """Test that AA data covers approximately 12 months."""
        adapter = AccountAggregatorAdapter()
        data = adapter.fetch("1")
        summary = data["summary"]

        assert len(summary) >= 11  # At least 11 months


class TestGSTAdapter:
    """Tests for GST registry data adapter."""

    def test_gst_fetch_valid_gstin(self):
        """Test deterministic GST data for valid GSTIN."""
        adapter = GSTAdapter()
        data = adapter.fetch("27AAGPT7202F1Z5")

        assert data is not None
        assert "vintage_date" in data
        assert "data_hash" in data
        assert "summary" in data

        # Verify schema
        assert isinstance(data["vintage_date"], datetime)
        assert isinstance(data["data_hash"], str)
        assert isinstance(data["summary"], list)

        # Verify summary structure
        if len(data["summary"]) > 0:
            row = data["summary"][0]
            assert "month" in row
            assert "sgst" in row
            assert "cgst" in row
            assert "igst" in row
            assert "turnover" in row

    def test_gst_deterministic_same_gstin(self):
        """Test that same GSTIN returns identical data."""
        adapter = GSTAdapter()
        data1 = adapter.fetch("27AAGPT7202F1Z5")
        data2 = adapter.fetch("27AAGPT7202F1Z5")

        # Should have same hash
        assert data1["data_hash"] == data2["data_hash"]
        assert len(data1["summary"]) == len(data2["summary"])

    def test_gst_different_gstins_different_data(self):
        """Test that different GSTINs return different data."""
        adapter = GSTAdapter()
        data1 = adapter.fetch("27AAGPT7202F1Z5")
        data2 = adapter.fetch("27AAGPT7202F1Z6")

        # Should have different hashes
        assert data1["data_hash"] != data2["data_hash"]

    def test_gst_invalid_gstin_format(self):
        """Test error handling for invalid GSTIN format."""
        adapter = GSTAdapter()

        with pytest.raises(ValueError):
            adapter.fetch("invalid")

        with pytest.raises(ValueError):
            adapter.fetch("27AAGPT7202F1")  # Too short

        with pytest.raises(ValueError):
            adapter.fetch("27AAGPT7202F1Z5X")  # Too long

    def test_gst_positive_taxes(self):
        """Test that all tax amounts are non-negative."""
        adapter = GSTAdapter()
        data = adapter.fetch("27AAGPT7202F1Z5")

        for row in data["summary"]:
            assert row["sgst"] >= 0
            assert row["cgst"] >= 0
            assert row["igst"] >= 0
            assert row["turnover"] >= 0


class TestAdapterIntegration:
    """Integration tests across multiple adapters."""

    def test_all_adapters_return_valid_schema(self):
        """Test that all adapters return valid schemas."""
        upi = UPIAdapter().fetch("1")
        aa = AccountAggregatorAdapter().fetch("1")
        gst = GSTAdapter().fetch("27AAGPT7202F1Z5")

        # All should have vintage_date and data_hash
        assert "vintage_date" in upi
        assert "data_hash" in upi
        assert "vintage_date" in aa
        assert "data_hash" in aa
        assert "vintage_date" in gst
        assert "data_hash" in gst

    def test_vintage_dates_are_recent(self):
        """Test that vintage dates are from the last 12+ months."""
        from datetime import datetime, timedelta

        # Use naive datetime to match adapter output
        now = datetime.now()
        one_year_ago = now - timedelta(days=400)

        upi = UPIAdapter().fetch("1")
        aa = AccountAggregatorAdapter().fetch("1")
        gst = GSTAdapter().fetch("27AAGPT7202F1Z5")

        # All vintage dates should be older than now (but not too old)
        assert upi["vintage_date"] < now
        assert upi["vintage_date"] > one_year_ago

        assert aa["vintage_date"] < now
        assert aa["vintage_date"] > one_year_ago

        assert gst["vintage_date"] < now
        assert gst["vintage_date"] > one_year_ago

