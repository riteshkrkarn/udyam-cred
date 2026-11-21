"""Tier Assignment engine: assign borrower to Tier 1, 2, or 3."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TierAssignmentResult:
    """Result of tier assignment."""

    tier: int  # 1, 2, or 3
    max_amount: float
    rate_adjustment: float
    tranche_plan: str  # "single" | "2-3" | "4+"
    tenure_months: int
    reasons: list[str]
    next_tier_criteria: list[str]


class TierAssignmentEngine:
    """Assign borrower to lending tier based on verified data."""

    # Tier policies
    TIER_POLICIES = {
        1: {
            "min_verified_months": 6,
            "min_agreement_score": 0.7,
            "max_amount": 50000,
            "rate_adjustment": 4.0,
            "tranche_plan": "single",
            "tenure_months": 12,
            "requirements": [
                "6+ months of verified bank data (AA + UPI)",
                "No GST registration",
                "No Udyam registration",
                "Sales agreement score > 70%",
                "Shop location verified",
            ],
        },
        2: {
            "min_verified_months": 12,
            "min_agreement_score": 0.65,
            "max_amount": 250000,
            "rate_adjustment": 2.0,
            "tranche_plan": "2-3",
            "tenure_months": 24,
            "requirements": [
                "12+ months of verified data (AA + GST/UPI)",
                "GST registered",
                "No Udyam registration",
                "Sales agreement score > 65%",
            ],
        },
        3: {
            "min_verified_months": 24,
            "min_agreement_score": 0.60,
            "max_amount": 1000000,
            "rate_adjustment": 0.0,
            "tranche_plan": "4+",
            "tenure_months": 36,
            "requirements": [
                "24+ months of verified data (AA + GST)",
                "Udyam registered",
                "Prior repayment history with us",
            ],
        },
    }

    @staticmethod
    def assign_tier(
        verified_months: int,
        source_agreement_score: float,
        photo_verified: bool,
        gst_registered: bool,
        udyam_registered: bool,
        prior_repayment_history: Optional[bool] = None,
    ) -> TierAssignmentResult:
        """
        Assign borrower to a tier based on criteria.

        Args:
            verified_months: Number of verified months (AA + GST/UPI overlap)
            source_agreement_score: Agreement score between sources (0-1)
            photo_verified: Whether shop location was verified
            gst_registered: Whether borrower is registered for GST
            udyam_registered: Whether borrower has Udyam registration
            prior_repayment_history: Whether customer has prior repayment record with us

        Returns:
            TierAssignmentResult with tier and details
        """
        reasons = []
        next_tier_criteria = []

        # Check Tier 3 eligibility
        if (
            verified_months >= TierAssignmentEngine.TIER_POLICIES[3][
                "min_verified_months"
            ]
            and gst_registered
            and udyam_registered
            and (prior_repayment_history is True)
        ):
            reasons.append(
                f"Verified {verified_months} months of bank data with GST/UPI"
            )
            reasons.append("Udyam registered")
            reasons.append("Prior repayment record confirmed")
            reasons.append("Tier 3: Established business with verified track record")

            next_tier_criteria.append("Maintain on-time repayment for tenure")

            return TierAssignmentResult(
                tier=3,
                max_amount=TierAssignmentEngine.TIER_POLICIES[3]["max_amount"],
                rate_adjustment=TierAssignmentEngine.TIER_POLICIES[3][
                    "rate_adjustment"
                ],
                tranche_plan=TierAssignmentEngine.TIER_POLICIES[3]["tranche_plan"],
                tenure_months=TierAssignmentEngine.TIER_POLICIES[3]["tenure_months"],
                reasons=reasons,
                next_tier_criteria=next_tier_criteria,
            )

        # Check Tier 2 eligibility
        if (
            verified_months >= TierAssignmentEngine.TIER_POLICIES[2][
                "min_verified_months"
            ]
            and gst_registered
            and source_agreement_score
            >= TierAssignmentEngine.TIER_POLICIES[2]["min_agreement_score"]
        ):
            reasons.append(
                f"Verified {verified_months} months of bank data (requires 12+)"
            )
            reasons.append("GST registered")
            reasons.append(
                f"Sales sources agree {source_agreement_score * 100:.0f}% (requires 65%+)"
            )
            reasons.append("Tier 2: Registered business with GST compliance")

            if not udyam_registered:
                next_tier_criteria.append(
                    "Register for Udyam (10-minute process) to unlock Tier 3 (up to ₹10L)"
                )
            if prior_repayment_history is not True:
                next_tier_criteria.append("Build 6+ months on-time repayment history")

            return TierAssignmentResult(
                tier=2,
                max_amount=TierAssignmentEngine.TIER_POLICIES[2]["max_amount"],
                rate_adjustment=TierAssignmentEngine.TIER_POLICIES[2][
                    "rate_adjustment"
                ],
                tranche_plan=TierAssignmentEngine.TIER_POLICIES[2]["tranche_plan"],
                tenure_months=TierAssignmentEngine.TIER_POLICIES[2]["tenure_months"],
                reasons=reasons,
                next_tier_criteria=next_tier_criteria,
            )

        # Check Tier 1 eligibility (default)
        if (
            verified_months >= TierAssignmentEngine.TIER_POLICIES[1][
                "min_verified_months"
            ]
            and not gst_registered
            and not udyam_registered
            and source_agreement_score
            >= TierAssignmentEngine.TIER_POLICIES[1]["min_agreement_score"]
            and photo_verified
        ):
            reasons.append(
                f"Verified {verified_months} months of bank data (requires 6+)"
            )
            reasons.append(
                f"AA and UPI agree on sales {source_agreement_score * 100:.0f}%"
            )
            reasons.append("Shop location verified with rent agreement")
            reasons.append("Tier 1: Quick loan for emerging businesses")

            next_tier_criteria.append(
                "Register for GST to unlock Tier 2 (up to ₹2.5L)"
            )
            next_tier_criteria.append("Maintain 6+ months of on-time repayment")

            return TierAssignmentResult(
                tier=1,
                max_amount=TierAssignmentEngine.TIER_POLICIES[1]["max_amount"],
                rate_adjustment=TierAssignmentEngine.TIER_POLICIES[1][
                    "rate_adjustment"
                ],
                tranche_plan=TierAssignmentEngine.TIER_POLICIES[1]["tranche_plan"],
                tenure_months=TierAssignmentEngine.TIER_POLICIES[1]["tenure_months"],
                reasons=reasons,
                next_tier_criteria=next_tier_criteria,
            )

        # Rejection: insufficient data
        if verified_months < 6:
            reasons.append(
                f"Only {verified_months} months of verified data (requires 6+)"
            )
            next_tier_criteria.append("Provide 6+ months of bank statement history")
        elif not gst_registered:
            reasons.append("Not registered for GST")
            next_tier_criteria.append("Register for GST to qualify for lending")
        elif source_agreement_score < 0.65:
            reasons.append(
                f"Sales sources only agree {source_agreement_score * 100:.0f}% (requires 65%+)"
            )
            next_tier_criteria.append("Ensure consistency between sales records")
        elif not photo_verified:
            reasons.append("Shop location could not be verified")
            next_tier_criteria.append("Provide clear geo-tagged photo of shop")

        return TierAssignmentResult(
            tier=0,  # Rejected
            max_amount=0,
            rate_adjustment=0.0,
            tranche_plan="none",
            tenure_months=0,
            reasons=reasons,
            next_tier_criteria=next_tier_criteria,
        )
