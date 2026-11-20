"""Abstract base adapter interface for external data sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    """Abstract adapter interface for external data sources."""

    @abstractmethod
    def fetch(self, identifier: str) -> Dict[str, Any]:
        """Fetch data from the external source.

        Args:
            identifier: Shop ID (for UPI/AA) or GSTIN (for GST registry)

        Returns:
            Dictionary with keys:
                - vintage_date: datetime object (earliest date of available data)
                - data_hash: str (SHA256 hash of data_json)
                - transactions: list (for transaction-level data) or summary: dict (for aggregated data)

        Raises:
            ValueError: If identifier is invalid or data not found
            Exception: On network/service errors
        """
        pass
