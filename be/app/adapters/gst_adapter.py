"""Mock GST registry adapter returning deterministic monthly GST turnover data."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.adapters.base import BaseAdapter


class GSTAdapter(BaseAdapter):
    """Mock GST registry data adapter with deterministic test data."""

    # Deterministic test data: gstin -> (monthly_avg_turnover, seed)
    TEST_DATA = {
        "27AAGPT7202F1Z5": (110000, 3001),
        "27AAGPT7202F1Z6": (150000, 3002),
    }

    @staticmethod
    def get_gst_data(gstin: str) -> Dict[str, Any]:
        """Fetch mock GST turnover data for the last 12 months.

        Args:
            gstin: GSTIN string (15 chars)

        Returns:
            {
                "vintage_date": datetime,  # 12 months ago from today
                "data_hash": str,
                "summary": [
                    {
                        "month": "YYYY-MM",
                        "sgst": float,
                        "cgst": float,
                        "igst": float,
                        "turnover": float
                    },
                    ...
                ]
            }
        """
        if not isinstance(gstin, str) or len(gstin) != 15:
            raise ValueError(f"Invalid GSTIN format: {gstin}")

        # Get test data if available, otherwise generate based on GSTIN hash
        if gstin in GSTAdapter.TEST_DATA:
            monthly_avg_turnover, seed = GSTAdapter.TEST_DATA[gstin]
        else:
            # Use GSTIN as seed for determinism
            seed = int(gstin[:2]) * 100 + int(gstin[2:4])
            monthly_avg_turnover = 80000 + (seed * 1000) % 150000

        # Generate 12 months of data
        summary: List[Dict[str, Any]] = []
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=365)
        vintage_date = datetime.combine(start_date, datetime.min.time())

        # Use seed for deterministic generation
        import random

        rng = random.Random(seed)

        current_date = start_date

        while current_date <= today:
            if current_date.month == today.month and current_date.year == today.year:
                break

            month_str = current_date.strftime("%Y-%m")

            # Generate monthly GST filings
            monthly_turnover = monthly_avg_turnover * rng.uniform(0.6, 1.4)

            # Split into SGST, CGST, IGST (typical distribution)
            sgst = monthly_turnover * 0.09 * rng.uniform(0.8, 1.2)  # 9%
            cgst = monthly_turnover * 0.09 * rng.uniform(0.8, 1.2)  # 9%
            igst = monthly_turnover * 0.05 * rng.uniform(0.8, 1.2)  # 5%

            summary.append(
                {
                    "month": month_str,
                    "sgst": round(sgst, 2),
                    "cgst": round(cgst, 2),
                    "igst": round(igst, 2),
                    "turnover": round(monthly_turnover, 2),
                }
            )

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

    def fetch(self, gstin: str) -> Dict[str, Any]:
        """Fetch GST data for a given GSTIN."""
        return self.get_gst_data(gstin)
