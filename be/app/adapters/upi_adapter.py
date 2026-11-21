"""Mock UPI adapter returning deterministic 12-month transaction data."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.adapters.base import BaseAdapter


class UPIAdapter(BaseAdapter):
    """Mock UPI data adapter with deterministic test data."""

    # Deterministic test data: shop_id -> (monthly_avg_upi_inflow, base_seed)
    TEST_DATA = {
        1: (85000, 1001),
        2: (120000, 1002),
    }

    @staticmethod
    def get_upi_data(shop_id: int) -> Dict[str, Any]:
        """Fetch mock UPI transaction data for the last 12 months.

        Args:
            shop_id: Shop identifier (test data for 1, 2; random for others)

        Returns:
            {
                "vintage_date": datetime,  # 12 months ago from today
                "data_hash": str,
                "transactions": [
                    {
                        "date": "YYYY-MM-DD",
                        "utr": "UTR_XXXXX",
                        "amount": float,
                        "counterparty": "name"
                    },
                    ...
                ]
            }
        """
        # Get test data if available, otherwise generate based on shop_id
        if shop_id in UPIAdapter.TEST_DATA:
            monthly_avg, seed = UPIAdapter.TEST_DATA[shop_id]
        else:
            # For non-test shops, use shop_id as seed for determinism
            monthly_avg = 50000 + (shop_id * 5000) % 100000
            seed = 2000 + shop_id

        # Generate 12 months of data
        transactions: List[Dict[str, Any]] = []
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=365)
        vintage_date = datetime.combine(start_date, datetime.min.time())

        # Use seed for deterministic random-like generation
        import random

        rng = random.Random(seed)

        current_date = start_date
        while current_date <= today:
            # Generate 2-5 transactions per day
            num_transactions = rng.randint(2, 5)
            daily_total = 0

            for _ in range(num_transactions):
                # Amount varies around monthly average / 30
                base_amount = monthly_avg / 30
                amount = base_amount * rng.uniform(0.5, 1.8)
                daily_total += amount

                utr = f"UTR{seed}{current_date.strftime('%Y%m%d')}{_:02d}"
                counterparty_idx = rng.randint(0, 9)
                counterparty = f"Customer_{counterparty_idx}"

                transactions.append(
                    {
                        "date": current_date.isoformat(),
                        "utr": utr,
                        "amount": round(amount, 2),
                        "counterparty": counterparty,
                    }
                )

            current_date += timedelta(days=1)

        # Create data hash
        data_str = json.dumps(transactions, sort_keys=True)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()

        return {
            "vintage_date": vintage_date,
            "data_hash": data_hash,
            "transactions": transactions,
        }

    def fetch(self, shop_id: str) -> Dict[str, Any]:
        """Fetch UPI data for a given shop_id."""
        try:
            shop_id_int = int(shop_id)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid shop_id: {shop_id}")

        if shop_id_int <= 0:
            raise ValueError(f"shop_id must be positive, got {shop_id_int}")

        return self.get_upi_data(shop_id_int)
