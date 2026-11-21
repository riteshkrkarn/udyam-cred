"""Amount Rule engine: calculate approved loan amount."""
from dataclasses import dataclass


@dataclass
class AmountRuleResult:
    """Result of amount calculation."""

    approved_amount: float
    tier_cap: float
    verified_weight: float
    agreement_weight: float
    reasoning: str


class AmountRuleEngine:
    """Calculate approved loan amount based on tier and verification."""

    # Tier caps
    TIER_CAPS = {
        1: 50000,
        2: 250000,
        3: 1000000,
    }

    # Minimum verified months per tier
    TIER_MIN_MONTHS = {
        1: 6,
        2: 12,
        3: 24,
    }

    # GST coverage penalties
    GST_COVERAGE_LOWER_THRESHOLD = 0.8
    GST_COVERAGE_UPPER_THRESHOLD = 1.2
    GST_COVERAGE_PENALTY = 0.85  # Reduce amount by 15% if coverage is off

    @staticmethod
    def calculate_amount(
        tier: int,
        verified_months: int,
        source_agreement_score: float,
        gst_coverage: float = 1.0,
    ) -> AmountRuleResult:
        """
        Calculate approved loan amount.

        Formula:
            amount = tier_cap × verified_weight × agreement_weight × gst_penalty

        Args:
            tier: Tier number (1, 2, or 3)
            verified_months: Number of verified months
            source_agreement_score: Agreement score (0-1)
            gst_coverage: GST/purchases ratio (1.0 = perfect alignment)

        Returns:
            AmountRuleResult with calculation details
        """
        if tier not in {1, 2, 3}:
            return AmountRuleResult(
                approved_amount=0.0,
                tier_cap=0.0,
                verified_weight=0.0,
                agreement_weight=0.0,
                reasoning="Invalid tier",
            )

        tier_cap = AmountRuleEngine.TIER_CAPS[tier]
        tier_min = AmountRuleEngine.TIER_MIN_MONTHS[tier]

        # Verified weight: scale with months, cap at 1.0
        verified_weight = min(verified_months / tier_min, 1.0)

        # Agreement weight: directly the score
        agreement_weight = min(source_agreement_score, 1.0)

        # GST coverage penalty
        gst_penalty = 1.0
        gst_note = ""

        if gst_coverage < AmountRuleEngine.GST_COVERAGE_LOWER_THRESHOLD:
            gst_penalty = AmountRuleEngine.GST_COVERAGE_PENALTY
            gst_note = (
                f" (GST coverage {gst_coverage * 100:.0f}% is low, applying 15% penalty)"
            )
        elif gst_coverage > AmountRuleEngine.GST_COVERAGE_UPPER_THRESHOLD:
            gst_penalty = AmountRuleEngine.GST_COVERAGE_PENALTY
            gst_note = (
                f" (GST coverage {gst_coverage * 100:.0f}% is high, applying 15% penalty)"
            )
        else:
            gst_note = f" (GST coverage {gst_coverage * 100:.0f}% acceptable)"

        # Calculate approved amount
        approved_amount = tier_cap * verified_weight * agreement_weight * gst_penalty

        reasoning = (
            f"Tier {tier} cap ₹{tier_cap:,.0f}, "
            f"verified {verified_months}/{tier_min} months ({verified_weight * 100:.0f}%), "
            f"agreement {agreement_weight * 100:.0f}%, "
            f"result: ₹{approved_amount:,.0f}{gst_note}"
        )

        return AmountRuleResult(
            approved_amount=approved_amount,
            tier_cap=tier_cap,
            verified_weight=verified_weight,
            agreement_weight=agreement_weight,
            reasoning=reasoning,
        )
