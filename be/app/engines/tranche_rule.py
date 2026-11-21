"""Tranche rule engine for UdyamCred v2.

Determines when next tranche is eligible for release based on:
- Repayment record (on-time EMIs)
- Missed EMI count
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class EMI:
    """Represents one EMI (Equated Monthly Installment)."""
    due_date: datetime
    paid_date: Optional[datetime] = None
    status: str = "pending"  # pending | on_time | late | missed


@dataclass
class TrancheInput:
    """Input to the tranche rule engine."""
    tranche_index: int  # Which tranche (1, 2, 3, etc.)
    loan_amount: float
    emis: List[EMI]  # All EMIs disbursed so far
    missed_emi_count: int = 0


@dataclass
class TrancheOutput:
    """Output from the tranche rule engine."""
    eligible: bool  # Can the next tranche be released?
    tranche_amount: float
    condition_met: str  # Which condition was checked (for console)
    reasoning: str


def check_tranche_eligibility(input_data: TrancheInput, policy: dict) -> TrancheOutput:
    """
    Check if the next tranche is eligible for release.
    
    Logic:
    - Tranche 1: Released on approval (100% eligible immediately after loan approved)
    - Tranche 2: Eligible if 3+ on-time EMIs in last 6 months
    - Tranche 3: Eligible if 6+ on-time EMIs total
    
    Args:
        input_data: TrancheInput with EMI history
        policy: Policy dict with tranche_rule configuration
    
    Returns:
        TrancheOutput with eligibility, amount, condition, and reasoning
    """
    policy_tranche = policy.get("tranche_rule", {})
    tranche_key = f"tranche_{input_data.tranche_index + 1}"
    tranche_config = policy_tranche.get(tranche_key, {})
    
    # Tranche 1: Always eligible on approval
    if input_data.tranche_index == 0:
        amount_pct = tranche_config.get("amount_pct", 0.5)
        tranche_amount = input_data.loan_amount * amount_pct
        return TrancheOutput(
            eligible=tranche_config.get("release_on_approval", True),
            tranche_amount=tranche_amount,
            condition_met="Approval",
            reasoning="First tranche released on loan approval"
        )
    
    # Tranche 2+: Check release conditions
    release_conditions = tranche_config.get("release_conditions", [])
    if not release_conditions:
        # No conditions → always eligible
        amount_pct = tranche_config.get("amount_pct", 0.3)
        tranche_amount = input_data.loan_amount * amount_pct
        return TrancheOutput(
            eligible=True,
            tranche_amount=tranche_amount,
            condition_met="No conditions",
            reasoning="No release conditions defined"
        )
    
    condition = release_conditions[0]
    on_time_required = condition.get("on_time_emis_required", 3)
    within_months = condition.get("within_months", 6)
    
    # Count on-time EMIs
    on_time_count = sum(1 for emi in input_data.emis if emi.status == "on_time")
    
    amount_pct = tranche_config.get("amount_pct", 0.3)
    tranche_amount = input_data.loan_amount * amount_pct
    
    if on_time_count >= on_time_required:
        return TrancheOutput(
            eligible=True,
            tranche_amount=tranche_amount,
            condition_met=f"{on_time_required}+ on-time EMIs",
            reasoning=f"Tranche {input_data.tranche_index + 1} eligible: {on_time_count} on-time EMIs (>= {on_time_required} required)"
        )
    else:
        return TrancheOutput(
            eligible=False,
            tranche_amount=tranche_amount,
            condition_met=f"{on_time_required}+ on-time EMIs",
            reasoning=f"Tranche {input_data.tranche_index + 1} not yet eligible: {on_time_count} on-time EMIs (need {on_time_required})"
        )
