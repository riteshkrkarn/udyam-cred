"""Unit tests for tier_rule engine."""
import pytest
from app.engines.tier_rule import assign_tier, TierInput, TierOutput


@pytest.fixture
def policy():
    """Mock policy dict."""
    return {
        "tier_rule": {
            "tier_3_conditions": [{"repayment_record_months_gt": 0}],
            "tier_2_conditions": [{"bank_history_months_gte": 6}],
        }
    }


def test_tier_3_with_udyam_and_repayment(policy):
    """Tier 3: Udyam + repayment record."""
    input_data = TierInput(
        udyam_registered=True,
        repayment_record_months=3,  # Has repayment history
        gst_registered=False,
        bank_history_months=0
    )
    result = assign_tier(input_data, policy)
    assert result.tier == 3
    assert result.tier_name == "Tier 3"
    assert "Udyam" in result.decision_path
    assert result.confidence >= 0.90


def test_tier_2_with_gst(policy):
    """Tier 2: GST registered."""
    input_data = TierInput(
        udyam_registered=False,
        repayment_record_months=0,
        gst_registered=True,
        bank_history_months=0
    )
    result = assign_tier(input_data, policy)
    assert result.tier == 2
    assert result.tier_name == "Tier 2"
    assert "GST" in result.decision_path
    assert result.confidence >= 0.80


def test_tier_2_with_long_bank_history(policy):
    """Tier 2: Long bank history (6+ months)."""
    input_data = TierInput(
        udyam_registered=False,
        repayment_record_months=0,
        gst_registered=False,
        bank_history_months=12  # 12 months
    )
    result = assign_tier(input_data, policy)
    assert result.tier == 2
    assert result.tier_name == "Tier 2"
    assert "Bank history" in result.decision_path


def test_tier_1_no_evidence(policy):
    """Tier 1: No Tier 2 or 3 evidence."""
    input_data = TierInput(
        udyam_registered=False,
        repayment_record_months=0,
        gst_registered=False,
        bank_history_months=3  # Less than 6 months
    )
    result = assign_tier(input_data, policy)
    assert result.tier == 1
    assert result.tier_name == "Tier 1"
    assert "money-side" in result.decision_path


def test_tier_3_without_repayment_falls_to_tier_2(policy):
    """Udyam without repayment → doesn't qualify for Tier 3."""
    input_data = TierInput(
        udyam_registered=True,
        repayment_record_months=0,  # No repayment history with us
        gst_registered=True,  # But has GST
        bank_history_months=0
    )
    result = assign_tier(input_data, policy)
    assert result.tier == 2  # Falls to Tier 2 (GST registered)
    assert result.tier_name == "Tier 2"


def test_tier_precedence_tier_3_over_tier_2(policy):
    """Tier 3 takes precedence when both Tier 3 and Tier 2 conditions met."""
    input_data = TierInput(
        udyam_registered=True,
        repayment_record_months=6,  # Qualifies for Tier 3
        gst_registered=True,  # Also qualifies for Tier 2
        bank_history_months=12
    )
    result = assign_tier(input_data, policy)
    assert result.tier == 3  # Should pick Tier 3, not Tier 2
