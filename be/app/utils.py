"""Small shared helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Return a timezone-naive UTC datetime.

    SQLite strips tzinfo when storing datetimes, so DB-stored values come back
    naive. Using naive UTC consistently here keeps comparisons with stored
    values valid (no offset-naive vs offset-aware errors).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
