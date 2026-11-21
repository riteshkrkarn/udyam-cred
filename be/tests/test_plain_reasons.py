"""Tests for plain language reason generation.

Tests:
- Reason generation for Tier 1 with minimal verification
- Reason generation for Tier 2 with GST + bank data
- Reason generation for Tier 3 with Udyam + repayment history
- Next tier criteria shows clear next steps
- All tiers have at least 2-3 reasons explaining decision
- Source verification summary
- Verification checks summary
"""
import pytest
from app.templates.reasons import (
    generate_plain_reasons,
    generate_next_tier_criteria,
    generate_source_verification_summary,
    generate_verification_checks_summary,
    TIER_REASONS,
    NEXT_TIER_REASONS,
    SOURCE_REASONS,
    VERIFICATION_REASONS,
)


class TestTier1ReasonGeneration:
    """Test reason generation for Tier 1 approval."""

    def test_tier1_minimal_approval_reasons(self):
        """Test Tier 1 with minimal verification generates 2+ reasons."""
        decision = {
            "tier": 1,
            "verdict": "approved",
            "verified_months": 6,
            "source_agreement_score": 0.75,
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) >= 3, "Tier 1 should have at least 3 reasons"
        assert any("6 months" in r for r in reasons), "Should mention 6 months of data"
        assert any("Tier 1" in r for r in reasons), "Should mention Tier 1"

    def test_tier1_strong_data_reasons(self):
        """Test Tier 1 with strong data generates appropriate reasons."""
        decision = {
            "tier": 1,
            "verdict": "approved",
            "verified_months": 10,
            "source_agreement_score": 0.82,
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) >= 4, "Tier 1 with strong data should have 4+ reasons"
        assert any("10 months" in r for r in reasons), "Should mention 10 months"
        assert any("excellent" in r.lower() or "82%" in r for r in reasons), "Should mention agreement"

    def test_tier1_mentions_photo_verification(self):
        """Test Tier 1 reasons mention photo verification."""
        decision = {
            "tier": 1,
            "verdict": "approved",
            "verified_months": 8,
            "source_agreement_score": 0.78,
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert any("photo" in r.lower() or "location" in r.lower() for r in reasons), \
            "Should mention photo or location verification"

    def test_tier1_next_tier_to_gst(self):
        """Test Tier 1 next tier criteria suggests GST registration."""
        decision = {
            "tier": 1,
            "verified_months": 6,
            "source_agreement_score": 0.75,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "photo_verified": True,
        }
        next_steps = generate_next_tier_criteria(decision)
        assert len(next_steps) > 0, "Should have next tier criteria"
        assert any("GST" in step for step in next_steps), "Should mention GST for Tier 2"
        assert any("Tier 2" in step for step in next_steps), "Should mention Tier 2"


class TestTier2ReasonGeneration:
    """Test reason generation for Tier 2 approval."""

    def test_tier2_with_gst_reasons(self):
        """Test Tier 2 with GST generates appropriate reasons."""
        decision = {
            "tier": 2,
            "verdict": "approved",
            "verified_months": 12,
            "source_agreement_score": 0.80,
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": True,
            "gst_coverage": 0.85,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa", "gst"],
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) >= 4, "Tier 2 should have at least 4 reasons"
        assert any("12 months" in r for r in reasons), "Should mention 12 months"
        assert any("GST" in r for r in reasons), "Should mention GST registration"
        assert any("Tier 2" in r for r in reasons), "Should mention Tier 2"

    def test_tier2_gst_coverage_mentioned(self):
        """Test Tier 2 reasons mention GST coverage."""
        decision = {
            "tier": 2,
            "verdict": "approved",
            "verified_months": 12,
            "source_agreement_score": 0.80,
            "gst_registered": True,
            "gst_coverage": 0.82,
            "udyam_registered": False,
            "photo_verified": True,
            "prior_repayment_history": None,
            "sources_used": ["aa", "gst"],
        }
        reasons = generate_plain_reasons(decision)
        assert any("GST" in r and "%" in r for r in reasons), \
            "Should mention GST coverage percentage"

    def test_tier2_next_tier_to_udyam(self):
        """Test Tier 2 next tier criteria suggests Udyam for Tier 3."""
        decision = {
            "tier": 2,
            "verified_months": 12,
            "source_agreement_score": 0.80,
            "gst_registered": True,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "photo_verified": True,
        }
        next_steps = generate_next_tier_criteria(decision)
        assert len(next_steps) > 0, "Should have next tier criteria"
        assert any("Udyam" in step for step in next_steps), "Should mention Udyam for Tier 3"
        assert any("Tier 3" in step for step in next_steps), "Should mention Tier 3"


class TestTier3ReasonGeneration:
    """Test reason generation for Tier 3 approval."""

    def test_tier3_with_full_documentation_reasons(self):
        """Test Tier 3 with full documentation generates appropriate reasons."""
        decision = {
            "tier": 3,
            "verdict": "approved",
            "verified_months": 24,
            "source_agreement_score": 0.90,
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": True,
            "gst_coverage": 0.92,
            "udyam_registered": True,
            "prior_repayment_history": True,
            "sources_used": ["aa", "gst", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) >= 5, "Tier 3 should have at least 5 reasons"
        assert any("24 months" in r for r in reasons), "Should mention 24 months"
        assert any("Udyam" in r for r in reasons), "Should mention Udyam"
        assert any("Tier 3" in r for r in reasons), "Should mention Tier 3"
        assert any("repayment" in r.lower() for r in reasons), "Should mention repayment history"

    def test_tier3_mentions_all_sources(self):
        """Test Tier 3 reasons mention multiple sources."""
        decision = {
            "tier": 3,
            "verdict": "approved",
            "verified_months": 24,
            "source_agreement_score": 0.85,
            "gst_registered": True,
            "udyam_registered": True,
            "prior_repayment_history": True,
            "photo_verified": True,
            "sources_used": ["aa", "gst", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert any("three" in r.lower() or "all" in r.lower() for r in reasons), \
            "Should mention three data sources"

    def test_tier3_next_tier_maintain_status(self):
        """Test Tier 3 next tier criteria focuses on maintaining status."""
        decision = {
            "tier": 3,
            "verified_months": 24,
            "source_agreement_score": 0.85,
            "gst_registered": True,
            "udyam_registered": True,
            "prior_repayment_history": True,
            "photo_verified": True,
        }
        next_steps = generate_next_tier_criteria(decision)
        assert len(next_steps) > 0, "Should have maintenance steps"
        assert any("repayment" in step.lower() or "EMI" in step for step in next_steps), \
            "Should focus on maintaining repayment"


class TestRejectionReasons:
    """Test reason generation for rejected applications."""

    def test_rejection_insufficient_data_months(self):
        """Test rejection reasons when insufficient data months."""
        decision = {
            "tier": 0,
            "verdict": "rejected",
            "verified_months": 3,
            "source_agreement_score": 0.75,
            "photo_verified": True,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa"],
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) >= 2, "Rejection should have reasons"
        assert any("3 months" in r for r in reasons), "Should mention insufficient months"

    def test_rejection_low_agreement_score(self):
        """Test rejection reasons when source agreement is low."""
        decision = {
            "tier": 0,
            "verdict": "rejected",
            "verified_months": 6,
            "source_agreement_score": 0.45,
            "photo_verified": True,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) >= 2, "Rejection should have reasons"
        assert any("45%" in r or "agreement" in r.lower() for r in reasons), \
            "Should mention low agreement"

    def test_rejection_no_photo_verification(self):
        """Test rejection reasons when photo not verified."""
        decision = {
            "tier": 0,
            "verdict": "rejected",
            "verified_months": 6,
            "source_agreement_score": 0.75,
            "photo_verified": False,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa", "upi"],
        }
        reasons = generate_plain_reasons(decision)
        assert any("photo" in r.lower() or "location" in r.lower() for r in reasons), \
            "Should mention photo verification failure"

    def test_rejection_next_steps(self):
        """Test rejection includes actionable next steps."""
        decision = {
            "tier": 0,
            "verdict": "rejected",
            "verified_months": 3,
            "source_agreement_score": 0.45,
            "photo_verified": False,
            "gst_registered": False,
            "udyam_registered": False,
            "prior_repayment_history": None,
            "sources_used": ["aa"],
        }
        next_steps = generate_next_tier_criteria(decision)
        assert len(next_steps) > 0, "Should provide next steps for rejected application"
        # Should have guidance on what's missing
        assert any(
            "bank" in step.lower() or "photo" in step.lower() or "consistent" in step.lower()
            for step in next_steps
        ), "Should guide on missing requirements"


class TestSourceVerificationSummary:
    """Test source verification summary generation."""

    def test_source_summary_with_aa(self):
        """Test source summary mentions AA data."""
        decision = {
            "sources_used": ["aa"],
            "aa_monthly_avg": 50000,
            "gst_monthly_avg": None,
            "upi_monthly_avg": None,
        }
        summary = generate_source_verification_summary(decision)
        assert len(summary) > 0, "Should generate summary"
        assert any("Bank" in s or "AA" in s for s in summary), "Should mention bank data"

    def test_source_summary_with_multiple_sources(self):
        """Test source summary with multiple sources."""
        decision = {
            "sources_used": ["aa", "gst", "upi"],
            "aa_monthly_avg": 50000,
            "gst_monthly_avg": 48000,
            "upi_monthly_avg": 45000,
        }
        summary = generate_source_verification_summary(decision)
        assert len(summary) >= 3, "Should mention all sources"
        assert any("Bank" in s for s in summary), "Should mention bank"
        assert any("GST" in s for s in summary), "Should mention GST"
        assert any("UPI" in s for s in summary), "Should mention UPI"

    def test_source_summary_formats_amounts(self):
        """Test source summary formats amounts correctly."""
        decision = {
            "sources_used": ["aa"],
            "aa_monthly_avg": 125000,
            "gst_monthly_avg": None,
            "upi_monthly_avg": None,
        }
        summary = generate_source_verification_summary(decision)
        assert any("125" in s or "1,25,000" in s for s in summary), \
            "Should format amount with separators"


class TestVerificationChecksSummary:
    """Test verification checks summary generation."""

    def test_checks_summary_all_passed(self):
        """Test verification checks when all passed."""
        decision = {
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": True,
            "udyam_registered": True,
        }
        checks = generate_verification_checks_summary(decision)
        assert len(checks) >= 3, "Should list all checks"
        assert any("✓" in c for c in checks), "Should mark passed checks"

    def test_checks_summary_partial_passed(self):
        """Test verification checks with partial pass."""
        decision = {
            "photo_verified": True,
            "location_verified": False,
            "gst_registered": True,
            "udyam_registered": False,
        }
        checks = generate_verification_checks_summary(decision)
        assert any("✓" in c for c in checks), "Should mark passed checks"
        assert any("✗" in c or "◯" in c for c in checks), "Should mark failed or optional checks"

    def test_checks_summary_tier_1_no_requirements(self):
        """Test Tier 1 marks GST and Udyam as optional."""
        decision = {
            "photo_verified": True,
            "location_verified": True,
            "gst_registered": False,
            "udyam_registered": False,
        }
        checks = generate_verification_checks_summary(decision)
        assert any("◯" in c and "GST" in c for c in checks), \
            "Should mark GST as optional for Tier 1"
        assert any("◯" in c and "Udyam" in c for c in checks), \
            "Should mark Udyam as optional for Tier 1"


class TestReasonDictionariesPopulated:
    """Test that all reason dictionaries have content."""

    def test_tier_reasons_populated(self):
        """Test TIER_REASONS dictionary is populated."""
        assert len(TIER_REASONS) > 0, "TIER_REASONS should have entries"
        assert any("verified" in k for k in TIER_REASONS.keys()), \
            "Should have verified-related reasons"
        assert any("tier" in k.lower() for k in TIER_REASONS.keys()), \
            "Should have tier-related reasons"

    def test_next_tier_reasons_populated(self):
        """Test NEXT_TIER_REASONS dictionary is populated."""
        assert len(NEXT_TIER_REASONS) > 0, "NEXT_TIER_REASONS should have entries"
        assert any("t1" in k or "t2" in k or "t3" in k for k in NEXT_TIER_REASONS.keys()), \
            "Should have tier progression reasons"

    def test_source_reasons_populated(self):
        """Test SOURCE_REASONS dictionary is populated."""
        assert len(SOURCE_REASONS) > 0, "SOURCE_REASONS should have entries"
        assert any("agreement" in k for k in SOURCE_REASONS.keys()), \
            "Should have source agreement reasons"

    def test_verification_reasons_populated(self):
        """Test VERIFICATION_REASONS dictionary is populated."""
        assert len(VERIFICATION_REASONS) > 0, "VERIFICATION_REASONS should have entries"
        assert any("photo" in k or "rent" in k for k in VERIFICATION_REASONS.keys()), \
            "Should have verification-related reasons"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimal_decision_data(self):
        """Test generation with minimal decision data."""
        decision = {
            "tier": 1,
            "verdict": "approved",
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) > 0, "Should handle minimal data gracefully"

    def test_missing_optional_fields(self):
        """Test generation when optional fields are missing."""
        decision = {
            "tier": 2,
            "verdict": "approved",
            "verified_months": 12,
            "source_agreement_score": 0.80,
            # Missing: photo_verified, gst_coverage, etc.
        }
        reasons = generate_plain_reasons(decision)
        assert len(reasons) > 0, "Should handle missing optional fields"

    def test_boundary_agreement_score(self):
        """Test reason generation at boundary agreement scores."""
        for score in [0.60, 0.70, 0.85]:
            decision = {
                "tier": 2,
                "verdict": "approved",
                "verified_months": 12,
                "source_agreement_score": score,
                "gst_registered": True,
                "photo_verified": True,
                "sources_used": ["aa", "gst"],
            }
            reasons = generate_plain_reasons(decision)
            assert len(reasons) > 0, f"Should handle score {score}"
            assert any(f"{score * 100:.0f}%" in r for r in reasons), \
                f"Should mention exact score {score * 100:.0f}%"

    def test_boundary_months(self):
        """Test reason generation at boundary month counts."""
        for months in [5, 6, 11, 12, 23, 24]:
            decision = {
                "tier": 1 if months == 6 else (2 if months == 12 else 3),
                "verdict": "approved",
                "verified_months": months,
                "source_agreement_score": 0.80,
                "gst_registered": False if months < 12 else True,
                "udyam_registered": False if months < 24 else True,
                "photo_verified": True,
                "prior_repayment_history": True if months >= 24 else None,
                "sources_used": ["aa"],
            }
            reasons = generate_plain_reasons(decision)
            assert len(reasons) > 0, f"Should handle {months} months"
