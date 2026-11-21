"""Amount rule engine for UdyamCred v2.

Determines loan amount based on:
- Tier (1, 2, or 3)
- Verified evidence length (months)
- Inflow amounts
- Confidence score
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AmountInput:
    """Input to the amount rule engine."""
    tier: int  # 1, 2, or 3
    verified_months: int  # Months of verified evidence
    monthly_inflow_avg: float  # Average monthly inflow in INR
    monthly_inflow_std: float  # Std dev of inflows
    confidence: float  # Overall confidence score (0.0 to 1.0)


@dataclass
class AmountOutput:
    """Output from the amount rule engine."""
    loan_amount: float  # Final approved loan amount in INR
    tier_cap: float  # Tier limit
    evidence_multiplier: float  # Scaling factor based on verified history
    reasoning: str  # Human-readable explanation


def calculate_loan_amount(input_data: AmountInput, policy: dict) -> AmountOutput:
    """
    Calculate loan amount based on tier and verified evidence.
    
    Logic:
    - Tier 1: Strict cap, no scaling by evidence
    - Tier 2/3: Base amount scales with verified history (multiplier based on months)
    
    Formula:
      amount = min(
        tier_cap,
        monthly_inflow_avg * multiplier_for_months
      )
    
    Args:
        input_data: AmountInput with tier, inflows, verified history
        policy: Policy dict with amount_rule configuration
    
    Returns:
        AmountOutput with final amount, cap, multiplier, and reasoning
    """
    policy_amount = policy.get("amount_rule", {})
    tier_config = policy_amount.get(f"tier_{input_data.tier}", {})
    tier_cap = tier_config.get("absolute_cap", 50000)
    
    # Tier 1: Strict cap, no scaling
    if input_data.tier == 1:
        # Conservative: 25-30% of monthly inflow or cap, whichever is lower
        base_amount = min(input_data.monthly_inflow_avg * 0.25, tier_cap)
        return AmountOutput(
            loan_amount=base_amount,
            tier_cap=tier_cap,
            evidence_multiplier=1.0,
            reasoning=f"Tier 1 (money-side evidence only): 25% of monthly inflow ({input_data.monthly_inflow_avg:.0f}) capped at {tier_cap:.0f}"
        )
    
    # Tier 2 and 3: Scale by verified history
    multiplier = 1.0
    scaling_tiers = tier_config.get("evidence_scaling", [])
    for scale_entry in scaling_tiers:
        if input_data.verified_months >= scale_entry.get("verified_months", 0):
            multiplier = scale_entry.get("multiplier", 1.0)
    
    # Conservative calculation: 30-40% of monthly inflow, scaled
    base_amount = input_data.monthly_inflow_avg * multiplier * 0.30
    final_amount = min(base_amount, tier_cap)
    
    return AmountOutput(
        loan_amount=final_amount,
        tier_cap=tier_cap,
        evidence_multiplier=multiplier,
        reasoning=f"Tier {input_data.tier}: Base ({input_data.monthly_inflow_avg:.0f} x 0.30) x {multiplier:.1f} multiplier = {base_amount:.0f}, capped at {tier_cap:.0f} → {final_amount:.0f}"
    )
