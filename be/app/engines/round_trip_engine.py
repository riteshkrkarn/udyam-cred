"""Round Trip Detection Engine.

Detects circular money patterns (same counterparty in/out within short windows).
"""
from datetime import datetime, timedelta
from typing import Any, Optional


def detect_round_trip(
    upi_transactions: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Detect round-trip (circular) money patterns in UPI transactions.

    Simple version: Detect same counterparty in multiple transactions within 7 days.

    Args:
        upi_transactions: List of dicts with {date, amount, counterparty, ...}

    Returns:
        {
            score: float - 0 (no round-trip) to 1 (high confidence)
            flagged_transactions: list[int] - Indices of flagged transactions
            confidence: float - Confidence in the detection
        }
    """
    score = 0.0
    flagged = []
    confidence = 0.0

    if not upi_transactions or not isinstance(upi_transactions, list):
        return {"score": score, "flagged_transactions": flagged, "confidence": confidence}

    if len(upi_transactions) < 2:
        return {"score": score, "flagged_transactions": flagged, "confidence": confidence}

    # Track counterparties and their transactions
    counterparty_txns = {}  # {counterparty: [(idx, date, amount, direction), ...]}

    for idx, txn in enumerate(upi_transactions):
        if not isinstance(txn, dict):
            continue

        cp = txn.get("counterparty", txn.get("name", "Unknown"))
        try:
            txn_date = datetime.fromisoformat(
                txn.get("date", "").replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            continue

        amount = txn.get("amount", 0)
        direction = "out" if amount < 0 else "in"

        if cp not in counterparty_txns:
            counterparty_txns[cp] = []
        counterparty_txns[cp].append((idx, txn_date, abs(amount), direction))

    # Analyze patterns
    window = timedelta(days=7)
    detected_patterns = 0

    for cp, txns in counterparty_txns.items():
        if len(txns) < 2:
            continue

        # Sort by date
        txns.sort(key=lambda x: x[1])

        # Look for in/out pairs within 7 days
        for i in range(len(txns)):
            for j in range(i + 1, len(txns)):
                idx_i, date_i, amt_i, dir_i = txns[i]
                idx_j, date_j, amt_j, dir_j = txns[j]

                # Check if within 7 days
                if (date_j - date_i) > window:
                    break  # No more pairs in window

                # Check if opposite directions and similar amounts (within 10%)
                if dir_i != dir_j:
                    amt_diff = abs(amt_i - amt_j) / max(amt_i, amt_j, 1)
                    if amt_diff <= 0.1:
                        flagged.extend([idx_i, idx_j])
                        detected_patterns += 1

    # Calculate score and confidence
    if detected_patterns > 0:
        # Score based on number of patterns: more patterns = higher score
        score = min(1.0, detected_patterns * 0.3)
        confidence = min(0.95, 0.5 + detected_patterns * 0.2)
        # Remove duplicates from flagged
        flagged = list(set(flagged))
    else:
        score = 0.0
        confidence = 0.95

    return {
        "score": score,
        "flagged_transactions": sorted(flagged),
        "confidence": confidence,
    }
