"""Rate Engine - Determine interest rate based on risk band and tenor."""
from typing import Any


# MVP rate table - fixed rates for now
RATE_TABLE = {
    "Low": {
        12: 9.5,
        24: 9.0,
        36: 8.5,
    },
    "Moderate": {
        12: 11.5,
        24: 11.0,
        36: 10.5,
    },
    "High": {
        12: 13.5,
        24: 13.0,
        36: 12.5,
    },
    "Needs Review": {
        12: 15.0,
        24: 14.5,
        36: 14.0,
    },
}


def get_rate(
    risk_band: str = "Moderate",
    tenor_months: int = 12,
) -> dict[str, Any]:
    """
    Get interest rate based on risk band and tenor.

    Args:
        risk_band: Risk category (Low, Moderate, High, Needs Review)
        tenor_months: Loan duration in months (12, 24, or 36)

    Returns:
        {
            rate_percent: float - Annual interest rate as percentage
            band: str - Risk band used
            tenor: int - Tenor in months
        }
    """
    # Normalize inputs
    if risk_band not in RATE_TABLE:
        risk_band = "Moderate"

    # Find closest tenor if exact match not found
    valid_tenors = sorted(RATE_TABLE[risk_band].keys())
    if tenor_months not in valid_tenors:
        # Use closest tenor
        tenor_months = min(valid_tenors, key=lambda x: abs(x - tenor_months))

    rate = RATE_TABLE[risk_band].get(tenor_months, RATE_TABLE[risk_band][12])

    return {
        "rate_percent": rate,
        "band": risk_band,
        "tenor": tenor_months,
    }
