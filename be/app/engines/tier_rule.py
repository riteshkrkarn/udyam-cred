"""Tier rule engine for UdyamCred v2.

Assigns tier (1, 2, or 3) based on:
- Udyam registration + repayment record with us → Tier 3
- GST registration OR long steady bank history (6+ months) → Tier 2
- Otherwise → Tier 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TierInput:
    """Input to the tier rule engine."""
    udyam_registered: bool = False
    repayment_record_months: int = 0  # Months of repayment history with us (0 if none)
    gst_registered: bool = False
    bank_history_months: int = 0  # Months of verified bank history


@dataclass
class TierOutput:
    """Output from the tier rule engine."""
    tier: int  # 1, 2, or 3
    tier_name: str
    decision_path: str  # Human-readable explanation of which condition matched
    confidence: float  # 0.0 to 1.0


def assign_tier(input_data: TierInput, policy: dict) -> TierOutput:
    """
    Assign tier based on evidence available.
    
    Logic:
    - Tier 3 if: Udyam registered AND has repayment record with us
    - Tier 2 if: GST registered OR bank history >= 6 months
    - Otherwise: Tier 1
    
    Args:
        input_data: TierInput with borrower evidence
        policy: Policy dict with tier_rule configuration
    
    Returns:
        TierOutput with tier, name, decision path and confidence
    """
    policy_tier_rule = policy.get("tier_rule", {})
    min_bank_history_tier_2 = 6  # From policy
    
    # Check Tier 3 conditions
    tier_3_conditions = policy_tier_rule.get("tier_3_conditions", [{}])[0]
    if (input_data.udyam_registered and 
        input_data.repayment_record_months > tier_3_conditions.get("repayment_record_months_gt", 0)):
        return TierOutput(
            tier=3,
            tier_name="Tier 3",
            decision_path="Udyam registered + repayment record with us",
            confidence=0.95
        )
    
    # Check Tier 2 conditions
    if input_data.gst_registered:
        return TierOutput(
            tier=2,
            tier_name="Tier 2",
            decision_path="GST registered",
            confidence=0.85
        )
    
    if input_data.bank_history_months >= min_bank_history_tier_2:
        return TierOutput(
            tier=2,
            tier_name="Tier 2",
            decision_path=f"Bank history {input_data.bank_history_months} months (>= {min_bank_history_tier_2} months)",
            confidence=0.80
        )
    
    # Otherwise Tier 1
    return TierOutput(
        tier=1,
        tier_name="Tier 1",
        decision_path="No Tier 2 or 3 evidence; money-side evidence only",
        confidence=0.60
    )
