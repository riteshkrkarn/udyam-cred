"""Tranche Rule engine: check eligibility for next tranche release."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Tranche, RepaymentRecord


@dataclass
class TrancheRuleResult:
    """Result of tranche eligibility check."""

    eligible: bool
    reason: str
    release_date: Optional[datetime]


class TrancheRuleEngine:
    """Check if next tranche is eligible based on repayment history."""

    @staticmethod
    def check_eligibility(
        application_id: int,
        tranche_num: int,
        db: Session,
    ) -> TrancheRuleResult:
        """
        Check if next tranche is eligible.

        Eligibility requirement: All EMIs from previous tranches must be on-time.

        Args:
            application_id: Application ID
            tranche_num: Tranche number to check eligibility for
            db: Database session

        Returns:
            TrancheRuleResult with eligibility status
        """
        # Get all tranches for this application, ordered by tranche_num
        tranches = (
            db.query(Tranche)
            .filter(Tranche.application_id == application_id)
            .order_by(Tranche.tranche_num)
            .all()
        )

        # Get the target tranche
        target_tranche = None
        for t in tranches:
            if t.tranche_num == tranche_num:
                target_tranche = t
                break

        if not target_tranche:
            return TrancheRuleResult(
                eligible=False,
                reason="Tranche not found",
                release_date=None,
            )

        if target_tranche.release_status == "released":
            return TrancheRuleResult(
                eligible=True,
                reason="Tranche already released",
                release_date=target_tranche.release_date,
            )

        # For first tranche, always eligible if pending
        if tranche_num == 1:
            if target_tranche.release_status == "pending":
                return TrancheRuleResult(
                    eligible=True,
                    reason="First tranche pending release",
                    release_date=target_tranche.release_date,
                )

        # For subsequent tranches, check all previous tranches' EMIs
        for prev_tranche in tranches:
            if prev_tranche.tranche_num >= tranche_num:
                break

            # Get all repayment records for this tranche
            repayments = (
                db.query(RepaymentRecord)
                .filter(RepaymentRecord.tranche_id == prev_tranche.id)
                .all()
            )

            # Check if any EMI is late, missed, or bounced
            for repay in repayments:
                if repay.payment_status in {"late", "missed", "bounced"}:
                    return TrancheRuleResult(
                        eligible=False,
                        reason=f"Tranche {prev_tranche.tranche_num} has {repay.payment_status} EMI #{repay.emi_num}",
                        release_date=None,
                    )

        return TrancheRuleResult(
            eligible=True,
            reason=f"All previous tranches' EMIs are on-time",
            release_date=target_tranche.release_date,
        )
