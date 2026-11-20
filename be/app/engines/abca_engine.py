"""ABCA Engine - Average Bank Credit Aggregator.

Calculates ABCA from two sources:
  - UPI: Average monthly inflows over last 12 months
  - AA: Average monthly bank deposits over last 12 months

Returns ABCA as average of both sources (or single source if one missing).
"""
from typing import Any, Optional


def calculate_abca(
    upi_data: Optional[dict[str, Any]] = None,
    aa_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Calculate Average Bank Credit Available (ABCA) from UPI and AA sources.

    Args:
        upi_data: Dict with structure {data: [{date, amount, ...}, ...], vintage_date}
        aa_data: Dict with structure {data: [{month, deposits, ...}, ...], vintage_date}

    Returns:
        {
            abca_value: float - Final ABCA estimate
            upi_avg: Optional[float] - Average monthly UPI inflows
            aa_avg: Optional[float] - Average monthly bank deposits
            confidence: float - 0.6-0.9 based on source agreement
            vintage_dates: {upi_vintage: Optional[str], aa_vintage: Optional[str]}
        }
    """
    upi_avg = None
    aa_avg = None
    upi_vintage = None
    aa_vintage = None
    confidence = 0.0

    # Calculate UPI average
    if upi_data and isinstance(upi_data, dict):
        transactions = upi_data.get("data", [])
        if transactions:
            total_inflows = sum(
                t.get("amount", 0)
                for t in transactions
                if isinstance(t, dict) and t.get("amount", 0) > 0
            )
            upi_avg = total_inflows / 12.0 if total_inflows > 0 else 0.0
            upi_vintage = upi_data.get("vintage_date")

    # Calculate AA average
    if aa_data and isinstance(aa_data, dict):
        deposits = aa_data.get("data", [])
        if deposits:
            total_deposits = sum(
                d.get("deposits", 0) for d in deposits if isinstance(d, dict)
            )
            aa_avg = total_deposits / 12.0 if total_deposits > 0 else 0.0
            aa_vintage = aa_data.get("vintage_date")

    # Calculate ABCA and confidence
    if upi_avg is not None and aa_avg is not None:
        # Both sources available
        abca_value = (upi_avg + aa_avg) / 2.0
        # Check agreement: within 20% means high confidence
        if upi_avg > 0:
            pct_diff = abs(upi_avg - aa_avg) / max(upi_avg, aa_avg)
            confidence = 0.9 if pct_diff <= 0.2 else 0.7
        else:
            confidence = 0.7
    elif upi_avg is not None:
        # Only UPI available
        abca_value = upi_avg
        confidence = 0.6
    elif aa_avg is not None:
        # Only AA available
        abca_value = aa_avg
        confidence = 0.6
    else:
        # No data available
        abca_value = 0.0
        confidence = 0.0

    return {
        "abca_value": max(0.0, abca_value),  # Ensure non-negative
        "upi_avg": upi_avg,
        "aa_avg": aa_avg,
        "confidence": confidence,
        "vintage_dates": {"upi_vintage": upi_vintage, "aa_vintage": aa_vintage},
    }
