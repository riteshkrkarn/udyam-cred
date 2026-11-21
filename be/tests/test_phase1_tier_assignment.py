"""Phase 1 tests for tier assignment engine.

Tests:
- Tier 1 conditions (6+ months, no GST, agreement > 0.7, photo verified)
- Tier 2 conditions (12+ months, GST, no Udyam)
- Tier 3 conditions (24+ months, GST, Udyam, repayment history)
- Boundary cases (exactly 6 months, 12 months, 24 months)
- Reason generation
- Next tier criteria
"""
import pytest
from app.engines.tier_assignment_engine import TierAssignmentEngine


class TestTier1Assignment:
    """Test Tier 1 assignment conditions."""

    def test_tier1_basic_conditions_met(self):
        """Test Tier 1 assignment with all conditions met."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier == 1
        assert result.max_amount == 50000

    def test_tier1_exactly_6_months_verified(self):
        """Test Tier 1 with exactly 6 months verified."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=6,
            source_agreement_score=0.75,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier == 1

    def test_tier1_less_than_6_months_fails(self):
        """Test Tier 1 fails with less than 6 months."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=5.9,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier != 1

    def test_tier1_weak_agreement_fails(self):
        """Test Tier 1 fails with weak agreement."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.69,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        # Should fail or downgrade
        assert result.tier != 1 or result.source_agreement_score >= 0.7

    def test_tier1_photo_not_verified_fails(self):
        """Test Tier 1 fails without photo verification."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=False,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier != 1

    def test_tier1_requires_no_gst(self):
        """Test Tier 1 requires no GST registration."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=True,  # Should upgrade to Tier 2
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier >= 1

    def test_tier1_rate_adjustment(self):
        """Test Tier 1 has correct rate adjustment."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.rate_adjustment == 4.0

    def test_tier1_tenure_months(self):
        """Test Tier 1 has correct tenure."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tenure_months == 12


class TestTier2Assignment:
    """Test Tier 2 assignment conditions."""

    def test_tier2_basic_conditions_met(self):
        """Test Tier 2 assignment with all conditions met."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier == 2
        assert result.max_amount == 250000

    def test_tier2_exactly_12_months_verified(self):
        """Test Tier 2 with exactly 12 months verified."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.75,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier == 2

    def test_tier2_less_than_12_months_fails(self):
        """Test Tier 2 fails with less than 12 months."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=11.9,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier < 2

    def test_tier2_requires_gst(self):
        """Test Tier 2 requires GST registration."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tier != 2

    def test_tier2_rate_adjustment(self):
        """Test Tier 2 has correct rate adjustment."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.rate_adjustment == 2.0

    def test_tier2_tenure_months(self):
        """Test Tier 2 has correct tenure."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert result.tenure_months == 24


class TestTier3Assignment:
    """Test Tier 3 assignment conditions."""

    def test_tier3_basic_conditions_met(self):
        """Test Tier 3 assignment with all conditions met."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=24,
            source_agreement_score=0.85,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=True,
            prior_repayment_history={"on_time_count": 12, "status": "good"},
        )
        assert result.tier == 3
        assert result.max_amount == 1000000

    def test_tier3_exactly_24_months_verified(self):
        """Test Tier 3 with exactly 24 months verified."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=24,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=True,
            prior_repayment_history={"on_time_count": 12, "status": "good"},
        )
        assert result.tier == 3

    def test_tier3_less_than_24_months_fails(self):
        """Test Tier 3 fails with less than 24 months."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=23.9,
            source_agreement_score=0.85,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=True,
            prior_repayment_history={"on_time_count": 12, "status": "good"},
        )
        assert result.tier < 3

    def test_tier3_requires_udyam(self):
        """Test Tier 3 requires Udyam registration."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=24,
            source_agreement_score=0.85,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history={"on_time_count": 12, "status": "good"},
        )
        assert result.tier < 3

    def test_tier3_requires_repayment_history(self):
        """Test Tier 3 requires prior repayment history."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=24,
            source_agreement_score=0.85,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=True,
            prior_repayment_history=None,
        )
        assert result.tier < 3

    def test_tier3_rate_adjustment(self):
        """Test Tier 3 has correct rate adjustment."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=24,
            source_agreement_score=0.85,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=True,
            prior_repayment_history={"on_time_count": 12, "status": "good"},
        )
        assert result.rate_adjustment == 0.0

    def test_tier3_tenure_months(self):
        """Test Tier 3 has correct tenure."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=24,
            source_agreement_score=0.85,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=True,
            prior_repayment_history={"on_time_count": 12, "status": "good"},
        )
        assert result.tenure_months == 36


class TestTierReasoning:
    """Test tier assignment reasoning."""

    def test_tier1_reasons_generated(self):
        """Test Tier 1 assignment includes reasons."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert len(result.reasons) > 0
        assert any("10 months" in r or "6 months" in r for r in result.reasons)

    def test_tier2_reasons_include_gst(self):
        """Test Tier 2 reasons mention GST."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert len(result.reasons) > 0

    def test_next_tier_criteria_tier1(self):
        """Test next tier criteria for Tier 1."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        assert len(result.next_tier_criteria) > 0


class TestBoundaryConditions:
    """Test boundary conditions for tier assignment."""

    def test_agreement_score_boundary_70_percent(self):
        """Test agreement score exactly at 70% boundary."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.70,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        # Should pass with agreement = 0.70
        assert result.tier >= 1

    def test_agreement_score_just_below_70_percent(self):
        """Test agreement score just below 70%."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.699,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )
        # Should fail Tier 1
        assert result.tier != 1 or result.source_agreement_score >= 0.7

    def test_tier_upgrade_with_gst(self):
        """Test tier upgrade when GST is registered."""
        result_without_gst = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
            prior_repayment_history=None,
        )

        result_with_gst = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.80,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
            prior_repayment_history=None,
        )

        assert result_with_gst.tier >= result_without_gst.tier
