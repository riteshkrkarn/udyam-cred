"""Tests for loan rules engine."""
import pytest
from app.engines.loan_rules_engine import apply_loan_rules


class TestLoanRulesEngine:
    """Test loan amount determination."""

    def test_all_constraints_apply(self):
        """Test when all constraints are applied."""
        result = apply_loan_rules(
            emi_capacity=100000,
            safe_amount=80000,
            policy_cap=500000,
        )

        # Minimum is safe_amount (80000)
        assert result["loan_amount"] == 80000
        assert result["binding_constraint"] == "safe_amount"
        assert result["rejection_reason"] is None

    def test_emi_capacity_is_binding(self):
        """Test when EMI capacity is the binding constraint."""
        result = apply_loan_rules(
            emi_capacity=50000,
            safe_amount=200000,
            policy_cap=500000,
        )

        assert result["loan_amount"] == 50000
        assert result["binding_constraint"] == "emi_capacity"

    def test_policy_cap_is_binding(self):
        """Test when policy cap is the binding constraint."""
        result = apply_loan_rules(
            emi_capacity=600000,
            safe_amount=600000,
            policy_cap=500000,
        )

        assert result["loan_amount"] == 500000
        assert result["binding_constraint"] == "policy_cap"

    def test_rejection_below_minimum(self):
        """Test rejection when loan amount is below minimum."""
        result = apply_loan_rules(
            emi_capacity=5000,
            safe_amount=5000,
            policy_cap=500000,
            minimum_loan=10000,
        )

        assert result["loan_amount"] == 0.0
        assert result["rejection_reason"] is not None
        assert "below minimum" in result["rejection_reason"]

    def test_rejection_at_minimum_boundary(self):
        """Test rejection when exactly at minimum."""
        result = apply_loan_rules(
            emi_capacity=10000,
            safe_amount=10000,
            policy_cap=500000,
            minimum_loan=10000,
        )

        # Should pass at exactly minimum
        assert result["loan_amount"] == 10000.0
        assert result["rejection_reason"] is None

    def test_rejection_just_below_minimum(self):
        """Test rejection just below minimum."""
        result = apply_loan_rules(
            emi_capacity=9999,
            safe_amount=9999,
            policy_cap=500000,
            minimum_loan=10000,
        )

        assert result["loan_amount"] == 0.0
        assert result["rejection_reason"] is not None

    def test_zero_emi_capacity_rejection(self):
        """Test rejection with zero EMI capacity."""
        result = apply_loan_rules(
            emi_capacity=0,
            safe_amount=100000,
            policy_cap=500000,
        )

        assert result["loan_amount"] == 0.0
        assert result["rejection_reason"] is not None

    def test_negative_constraints(self):
        """Test with negative constraint values."""
        result = apply_loan_rules(
            emi_capacity=-50000,
            safe_amount=100000,
            policy_cap=500000,
        )

        # Negative values treated as 0
        assert result["loan_amount"] == 0.0
        assert result["rejection_reason"] is not None

    def test_custom_minimum_loan(self):
        """Test custom minimum loan threshold."""
        result = apply_loan_rules(
            emi_capacity=25000,
            safe_amount=25000,
            policy_cap=500000,
            minimum_loan=20000,
        )

        assert result["loan_amount"] == 25000
        assert result["rejection_reason"] is None

    def test_binding_constraint_with_zero_values(self):
        """Test binding constraint identification with some zero values."""
        result = apply_loan_rules(
            emi_capacity=75000,
            safe_amount=0,
            policy_cap=500000,
        )

        assert result["loan_amount"] == 0.0
        assert result["binding_constraint"] is None  # All rejected

    def test_equal_constraints(self):
        """Test when multiple constraints are equal."""
        result = apply_loan_rules(
            emi_capacity=100000,
            safe_amount=100000,
            policy_cap=100000,
        )

        assert result["loan_amount"] == 100000
        # Any of the three could be binding when equal
        assert result["binding_constraint"] in [
            "emi_capacity",
            "safe_amount",
            "policy_cap",
        ]
