"""EMI Engine - Calculate household surplus, EMI capacity, and EMI schedules."""
from typing import Any, Optional


def calculate_household_surplus(
    abca: float,
    monthly_expenses: float,
    existing_liabilities: float,
    emi_share: float = 0.5,
) -> dict[str, float]:
    """
    Calculate household surplus and EMI capacity.

    Args:
        abca: Average Bank Credit Available (monthly average)
        monthly_expenses: Total monthly household expenses
        existing_liabilities: Total existing liabilities (e.g., outstanding loans)
        emi_share: Percentage of surplus available for EMI (default 0.5 = 50%)

    Returns:
        {
            household_surplus: float - Monthly surplus after expenses
            emi_capacity: float - Maximum EMI capacity (surplus * emi_share)
            monthly_surplus_after_emi: float - Surplus remaining after EMI
        }
    """
    # Estimate existing EMI: typical loan tenure 36 months, so monthly ≈ liabilities/36
    existing_emi = existing_liabilities / 36.0 if existing_liabilities > 0 else 0.0

    # Calculate household surplus
    household_surplus = max(0.0, abca - monthly_expenses - existing_emi)

    # Calculate EMI capacity
    emi_capacity = household_surplus * emi_share

    # Monthly surplus after EMI (informational)
    monthly_surplus_after_emi = household_surplus - emi_capacity

    return {
        "household_surplus": household_surplus,
        "emi_capacity": emi_capacity,
        "monthly_surplus_after_emi": monthly_surplus_after_emi,
    }


def calculate_emi_schedule(
    loan_amount: float,
    rate_percent: float,
    tenor_months: int,
) -> list[dict[str, Any]]:
    """
    Generate EMI schedule using standard amortization formula.

    EMI = (P * r * (1+r)^n) / ((1+r)^n - 1)
    where r = annual_rate / 12 / 100, n = tenor_months

    Args:
        loan_amount: Principal amount
        rate_percent: Annual interest rate as percentage
        tenor_months: Loan duration in months

    Returns:
        List of dicts: [{month, principal, interest, emi, balance}, ...]
    """
    if loan_amount <= 0 or tenor_months <= 0 or rate_percent < 0:
        return []

    # Convert annual rate to monthly decimal
    r = rate_percent / 12.0 / 100.0
    n = tenor_months
    p = loan_amount

    # Calculate EMI
    if r == 0:
        # No interest
        emi = p / n
    else:
        # Standard formula
        numerator = p * r * ((1 + r) ** n)
        denominator = ((1 + r) ** n) - 1
        emi = numerator / denominator

    schedule = []
    balance = p

    for month in range(1, n + 1):
        # Interest for this month
        interest = balance * r

        # Principal for this month
        principal = emi - interest

        # Remaining balance
        balance = max(0.0, balance - principal)

        schedule.append(
            {
                "month": month,
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "emi": round(emi, 2),
                "balance": round(balance, 2),
            }
        )

    return schedule
