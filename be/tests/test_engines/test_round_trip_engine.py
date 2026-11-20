"""Tests for round trip detection engine."""
import pytest
from datetime import datetime, timedelta
from app.engines.round_trip_engine import detect_round_trip


class TestRoundTripEngine:
    """Test round-trip detection."""

    def test_clean_transactions_no_round_trip(self):
        """Test with clean transactions (no round-trip)."""
        transactions = [
            {"date": "2023-01-01", "counterparty": "Supplier A", "amount": -5000},
            {"date": "2023-01-05", "counterparty": "Customer B", "amount": 3000},
            {"date": "2023-01-10", "counterparty": "Supplier C", "amount": -2000},
        ]

        result = detect_round_trip(transactions)

        assert result["score"] == 0.0
        assert len(result["flagged_transactions"]) == 0
        assert result["confidence"] > 0.9

    def test_circular_pattern_detected(self):
        """Test with circular transaction pattern."""
        base_date = datetime(2023, 1, 1)
        transactions = [
            {
                "date": (base_date).isoformat(),
                "counterparty": "Middleman",
                "amount": -10000,
            },
            {
                "date": (base_date + timedelta(days=2)).isoformat(),
                "counterparty": "Middleman",
                "amount": 10200,
            },
        ]

        result = detect_round_trip(transactions)

        # With 1 detected pattern, score = 1 * 0.3 = 0.3
        assert result["score"] > 0.0
        assert len(result["flagged_transactions"]) > 0

    def test_multiple_circular_patterns(self):
        """Test with multiple circular patterns."""
        base_date = datetime(2023, 1, 1)
        transactions = [
            {
                "date": (base_date).isoformat(),
                "counterparty": "Middleman A",
                "amount": -5000,
            },
            {
                "date": (base_date + timedelta(days=1)).isoformat(),
                "counterparty": "Middleman A",
                "amount": 5100,
            },
            {
                "date": (base_date + timedelta(days=3)).isoformat(),
                "counterparty": "Middleman B",
                "amount": -8000,
            },
            {
                "date": (base_date + timedelta(days=4)).isoformat(),
                "counterparty": "Middleman B",
                "amount": 8100,
            },
        ]

        result = detect_round_trip(transactions)

        assert result["score"] > 0.5
        assert len(result["flagged_transactions"]) >= 4

    def test_transactions_outside_window_not_flagged(self):
        """Test that transactions outside 7-day window are not flagged."""
        base_date = datetime(2023, 1, 1)
        transactions = [
            {
                "date": (base_date).isoformat(),
                "counterparty": "Supplier",
                "amount": -10000,
            },
            {
                "date": (base_date + timedelta(days=10)).isoformat(),
                "counterparty": "Supplier",
                "amount": 10000,
            },
        ]

        result = detect_round_trip(transactions)

        assert result["score"] == 0.0
        assert len(result["flagged_transactions"]) == 0

    def test_same_counterparty_different_directions_within_window(self):
        """Test same counterparty with in/out pattern within window."""
        base_date = datetime(2023, 1, 1)
        transactions = [
            {
                "date": (base_date).isoformat(),
                "counterparty": "Partner",
                "amount": 5000,
            },
            {
                "date": (base_date + timedelta(days=5)).isoformat(),
                "counterparty": "Partner",
                "amount": -4900,
            },
        ]

        result = detect_round_trip(transactions)

        # Should detect pattern (in then out, similar amounts, within 7 days)
        assert result["score"] > 0.0

    def test_no_transactions(self):
        """Test with no transactions."""
        result = detect_round_trip(None)

        assert result["score"] == 0.0
        assert len(result["flagged_transactions"]) == 0

    def test_single_transaction(self):
        """Test with single transaction."""
        transactions = [
            {"date": "2023-01-01", "counterparty": "Supplier", "amount": -5000}
        ]

        result = detect_round_trip(transactions)

        assert result["score"] == 0.0
        assert len(result["flagged_transactions"]) == 0

    def test_empty_list(self):
        """Test with empty transaction list."""
        result = detect_round_trip([])

        assert result["score"] == 0.0
        assert len(result["flagged_transactions"]) == 0
