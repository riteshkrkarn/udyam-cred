"""Vintage Engine - Determine earliest supported date from data sources.

Returns the earliest date where data is available from sources,
and counts how many sources support that date.
"""
from datetime import datetime
from typing import Any, Optional


def get_vintage(
    upi_vintage_date: Optional[str] = None,
    aa_vintage_date: Optional[str] = None,
) -> dict[str, Any]:
    """
    Determine earliest supported date from two sources.

    Args:
        upi_vintage_date: ISO format string or datetime for UPI data
        aa_vintage_date: ISO format string or datetime for AA data

    Returns:
        {
            earliest_date: Optional[str] - ISO format date
            supporting_sources_count: int - Number of sources with data
        }
    """
    dates = []
    supporting_count = 0

    # Parse UPI vintage date
    if upi_vintage_date:
        try:
            if isinstance(upi_vintage_date, str):
                upi_date = datetime.fromisoformat(upi_vintage_date.replace("Z", "+00:00"))
            else:
                upi_date = upi_vintage_date
            dates.append(upi_date)
            supporting_count += 1
        except (ValueError, AttributeError):
            pass

    # Parse AA vintage date
    if aa_vintage_date:
        try:
            if isinstance(aa_vintage_date, str):
                aa_date = datetime.fromisoformat(aa_vintage_date.replace("Z", "+00:00"))
            else:
                aa_date = aa_vintage_date
            dates.append(aa_date)
            supporting_count += 1
        except (ValueError, AttributeError):
            pass

    # Find earliest date
    if dates:
        earliest = min(dates)
        earliest_date = earliest.isoformat()
    else:
        earliest_date = None

    return {
        "earliest_date": earliest_date,
        "supporting_sources_count": supporting_count,
    }
