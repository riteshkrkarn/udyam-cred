"""Unit tests for amount_rule engine."""
import pytest
from app.engines.amount_rule import calculate_loan_amount, AmountInput, AmountOutput


@pytest.fixture
def policy():
    """Mock policy dict with amount rule config."""
    return {
        "amount_rule": {
            "tier_1": {
                "absolute_cap": 50000,
                "evidence_scaling_disabled": True,
            },
            "tier_2": {
                "absolute_cap": 500000,
                "evidence_scaling": [
                    {"verified_months": 6, "multiplier": 1.0},
                    {"verified_months": 12, "multiplier": 1.2},
                    {"verified_months": 24, "multiplier": 1.5},
                ],
            },
            "tier_3": {
                "absolute_cap": 1000000,
                "evidence_scaling": [
                    {"verified_months": 6, "multiplier": 1.2},
                    {"verified_months": 12, "multiplier": 1.5},
                    {"verified_months": 24, "multiplier": 2.0},
                ],
            },
        }
    }


def test_tier_1_strict_cap(policy):
    """Tier 1: Strictly capped, no scaling."""
    input_data = AmountInput(
        tier=1,
        verified_months=6,
        monthly_inflow_avg=100000,  # High inflow
        monthly_inflow_std=10000,
        confidence=0.8
    )
    result = calculate_loan_amount(input_data, policy)
    
    assert result.tier_cap == 50000
    assert result.loan_amount <= result.tier_cap
    assert result.evidence_multiplier == 1.0
    assert "Tier 1" in result.reasoning


def test_tier_2_scales_with_history(policy):
    """Tier 2: Amount scales with verified history."""
    # 6 months → 1.0x multiplier
    input_6mo = AmountInput(
        tier=2,
        verified_months=6,
        monthly_inflow_avg=50000,
        monthly_inflow_std=5000,
        confidence=0.7
    )
    result_6mo = calculate_loan_amount(input_6mo, policy)
    
    # 12 months → 1.2x multiplier (more)
    input_12mo = AmountInput(
        tier=2,
        verified_months=12,
        monthly_inflow_avg=50000,
        monthly_inflow_std=5000,
        confidence=0.7
    )
    result_12mo = calculate_loan_amount(input_12mo, policy)
    
    # 12-month amount should be higher than 6-month
    assert result_12mo.loan_amount > result_6mo.loan_amount
    assert result_12mo.evidence_multiplier == 1.2
    assert result_6mo.evidence_multiplier == 1.0


def test_tier_3_higher_cap_and_scaling(policy):
    """Tier 3: Higher cap and better scaling."""
    input_data = AmountInput(
        tier=3,
        verified_months=24,
        monthly_inflow_avg=50000,
        monthly_inflow_std=5000,
        confidence=0.9
    )
    result = calculate_loan_amount(input_data, policy)
    
    assert result.tier_cap == 1000000
    assert result.evidence_multiplier == 2.0


def test_amount_respects_tier_cap(policy):
    """Amount never exceeds tier cap."""
    input_data = AmountInput(
        tier=2,
        verified_months=24,
        monthly_inflow_avg=1000000,  # Very high inflow
        monthly_inflow_std=100000,
        confidence=0.95
    )
    result = calculate_loan_amount(input_data, policy)
    
    assert result.loan_amount <= result.tier_cap  # 500,000 for Tier 2
    assert result.tier_cap == 500000


def test_zero_inflow(policy):
    """Zero inflow → zero loan amount."""
    input_data = AmountInput(
        tier=2,
        verified_months=12,
        monthly_inflow_avg=0,
        monthly_inflow_std=0,
        confidence=0
    )
    result = calculate_loan_amount(input_data, policy)
    
    assert result.loan_amount == 0
    assert result.evidence_multiplier == 1.2


def test_tier_1_conservative_percentage(policy):
    """Tier 1: 25% of inflow is conservative."""
    input_data = AmountInput(
        tier=1,
        verified_months=12,
        monthly_inflow_avg=10000,
        monthly_inflow_std=1000,
        confidence=0.6
    )
    result = calculate_loan_amount(input_data, policy)
    
    # 25% of 10,000 = 2,500
    expected = 2500
    assert abs(result.loan_amount - expected) < 100  # Allow small rounding
