"""Stop rule engine for UdyamCred v2.

Determines if loan is frozen due to missed EMIs.

Logic:
- 2 missed EMIs (cumulative) → freeze tranches and open review
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class LoanStatus(str, Enum):
    """Loan status based on EMI payment record."""
    ACTIVE = "active"  # No missed EMIs
    AMBER = "amber"  # One missed EMI (warning)
    FROZEN = "frozen"  # Two+ missed EMIs (tranches paused)


@dataclass
class EMI:
    """Represents one EMI."""
    due_date: str  # ISO format
    paid_date: str | None
    status: str  # on_time | late | missed


@dataclass
class StopInput:
    """Input to the stop rule engine."""
    emis: List[EMI]  # All EMIs for this loan


@dataclass
class StopOutput:
    """Output from the stop rule engine."""
    status: LoanStatus
    missed_emi_count: int
    action_open_review: bool  # Should this trigger a review?
    reasoning: str


def evaluate_stop_rule(input_data: StopInput, policy: dict) -> StopOutput:
    """
    Evaluate stop rule: does the loan need to be frozen?
    
    Logic:
    - Count cumulative missed EMIs
    - 2+ missed → freeze, open review
    - 1 missed → warning (amber)
    - 0 missed → active (green)
    
    Args:
        input_data: StopInput with EMI list
        policy: Policy dict with stop_rule configuration
    
    Returns:
        StopOutput with status, missed count, review flag, reasoning
    """
    policy_stop = policy.get("stop_rule", {})
    threshold = policy_stop.get("missed_emis_threshold", 2)
    
    # Count missed EMIs
    missed_emis = [emi for emi in input_data.emis if emi.status == "missed"]
    missed_count = len(missed_emis)
    
    if missed_count >= threshold:
        return StopOutput(
            status=LoanStatus.FROZEN,
            missed_emi_count=missed_count,
            action_open_review=True,
            reasoning=f"Loan frozen: {missed_count} missed EMIs (>= threshold of {threshold}). Tranches paused. Review required."
        )
    elif missed_count == 1:
        return StopOutput(
            status=LoanStatus.AMBER,
            missed_emi_count=missed_count,
            action_open_review=False,
            reasoning=f"Warning: 1 missed EMI. One more missed EMI will freeze the loan."
        )
    else:
        return StopOutput(
            status=LoanStatus.ACTIVE,
            missed_emi_count=missed_count,
            action_open_review=False,
            reasoning="Loan is active. All EMIs on time or within grace period."
        )
