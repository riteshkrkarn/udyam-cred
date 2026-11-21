"""Loan Rules Engine - Apply policy constraints to determine final loan amount."""
from typing import Any, Optional


def apply_loan_rules(
    emi_capacity: float,
    safe_amount: float,
    policy_cap: float = 500000.0,
    minimum_loan: float = 10000.0,
) -> dict[str, Any]:
    """
    Apply loan rules to determine final approved loan amount.

    Loan amount = min(emi_capacity, safe_amount, policy_cap)

    Args:
        emi_capacity: Maximum EMI based on household surplus
        safe_amount: Maximum safe amount from capacity model
        policy_cap: Policy maximum loan amount (default 500,000)
        minimum_loan: Minimum loan amount to approve (default 10,000)

    Returns:
        {
            loan_amount: float - Final approved amount (0 if rejected)
            binding_constraint: str - Which constraint was limiting (emi_capacity, safe_amount, or policy_cap)
            rejection_reason: Optional[str] - Reason for rejection if rejected
        }
    """
    # Determine binding constraint
    constraints = {
        "emi_capacity": max(0.0, emi_capacity),
        "safe_amount": max(0.0, safe_amount),
        "policy_cap": max(0.0, policy_cap),
    }

    # Find minimum (binding) constraint
    loan_amount = min(constraints.values())
    binding_constraint = min(constraints, key=constraints.get)

    # Check for rejection
    rejection_reason = None

    if loan_amount < minimum_loan:
        rejection_reason = (
            f"Loan amount {loan_amount:.0f} below minimum {minimum_loan:.0f}. "
            f"Binding constraint: {binding_constraint}"
        )
        loan_amount = 0.0
    elif loan_amount <= 0:
        rejection_reason = "One or more constraints are non-positive"
        loan_amount = 0.0

    return {
        "loan_amount": loan_amount,
        "binding_constraint": binding_constraint if loan_amount > 0 else None,
        "rejection_reason": rejection_reason,
    }
