"""Mock Account Aggregator adapter returning deterministic 12-month bank data."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.adapters.base import BaseAdapter


class AccountAggregatorAdapter(BaseAdapter):
    """Mock Account Aggregator data adapter with deterministic test data."""

    # Deterministic test data: shop_id -> (monthly_avg_turnover, opening_balance)
    TEST_DATA = {
        1: (90000, 50000),
        2: (130000, 75000),
    }

    @staticmethod
    def get_aa_data(shop_id: int) -> Dict[str, Any]:
        """Fetch mock bank/account aggregator data for the last 12 months.

        Returns monthly opening/closing balance and turnover.

        Args:
            shop_id: Shop identifier (test data for 1, 2; generated for others)

        Returns:
            {
                "vintage_date": datetime,  # 12 months ago from today
                "data_hash": str,
                "summary": [
                    {
                        "month": "YYYY-MM",
                        "opening_balance": float,
                        "closing_balance": float,
                        "total_deposits": float,
                        "total_withdrawals": float,
                        "turnover": float
                    },
                    ...
                ]
            }
        """
        # Get test data if available, otherwise generate based on shop_id
        if shop_id in AccountAggregatorAdapter.TEST_DATA:
            monthly_avg_turnover, opening_balance = AccountAggregatorAdapter.TEST_DATA[
                shop_id
            ]
        else:
            # For non-test shops, use shop_id as seed for determinism
            monthly_avg_turnover = 60000 + (shop_id * 7000) % 120000
            opening_balance = 40000 + (shop_id * 3000) % 80000

        # Generate 12 months of data
        summary: List[Dict[str, Any]] = []
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=365)
        vintage_date = datetime.combine(start_date, datetime.min.time())

        # Use shop_id as seed for deterministic generation
        import random

        rng = random.Random(2000 + shop_id)

        current_balance = opening_balance
        current_date = start_date

        while current_date.month != today.month or current_date.year != today.year:
            month_str = current_date.strftime("%Y-%m")

            # Generate monthly turnover (deposits + withdrawals)
            monthly_turnover = monthly_avg_turnover * rng.uniform(0.7, 1.3)
            deposits = monthly_turnover * rng.uniform(0.5, 0.7)
            withdrawals = monthly_turnover * rng.uniform(0.3, 0.5)

            opening = current_balance
            closing = opening + deposits - withdrawals

            # Ensure balance doesn't go negative
            if closing < 0:
                closing = abs(closing) + 1000

            summary.append(
                {
                    "month": month_str,
                    "opening_balance": round(opening, 2),
                    "closing_balance": round(closing, 2),
                    "total_deposits": round(deposits, 2),
                    "total_withdrawals": round(withdrawals, 2),
                    "turnover": round(deposits + withdrawals, 2),
                }
            )

            current_balance = closing

            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        # Create data hash
        data_str = json.dumps(summary, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()

        return {
            "vintage_date": vintage_date,
            "data_hash": data_hash,
            "summary": summary,
        }

    def fetch(self, shop_id: str) -> Dict[str, Any]:
        """Fetch Account Aggregator data for a given shop_id."""
        try:
            shop_id_int = int(shop_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid shop_id: {shop_id}")

        if shop_id_int <= 0:
            raise ValueError(f"shop_id must be positive, got {shop_id_int}")

        return self.get_aa_data(shop_id_int)
