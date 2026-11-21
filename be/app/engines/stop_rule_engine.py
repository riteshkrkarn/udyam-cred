"""Stop Rule engine: freeze tranches on missed EMIs."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Tranche, RepaymentRecord, StopRule
from app.utils import utcnow_naive


@dataclass
class StopRuleResult:
    """Result of stop rule check."""

    should_freeze: bool
    missed_emi_count: int
    frozen_date: Optional[datetime]
    review_required: bool
    reason: str


class StopRuleEngine:
    """Apply stop rule: freeze on 2+ missed EMIs."""

    MISSED_EMI_THRESHOLD = 2  # Freeze if 2+ EMIs missed

    @staticmethod
    def check_and_apply(
        application_id: int,
        db: Session,
    ) -> StopRuleResult:
        """
        Check if stop rule should be applied.

        If 2+ EMIs are missed across all tranches, freeze further releases.

        Args:
            application_id: Application ID
            db: Database session

        Returns:
            StopRuleResult with freeze status
        """
        # Count missed EMIs across all tranches
        tranches = (
            db.query(Tranche)
            .filter(Tranche.application_id == application_id)
            .all()
        )

        missed_count = 0
        for tranche in tranches:
            missed_repayments = (
                db.query(RepaymentRecord)
                .filter(
                    RepaymentRecord.tranche_id == tranche.id,
                    RepaymentRecord.payment_status.in_({"missed", "bounced"}),
                )
                .all()
            )
            missed_count += len(missed_repayments)

        # Check existing stop rule
        existing_stop = (
            db.query(StopRule)
            .filter(StopRule.application_id == application_id)
            .first()
        )

        should_freeze = missed_count >= StopRuleEngine.MISSED_EMI_THRESHOLD

        if should_freeze and not existing_stop:
            # Create new stop rule
            now = utcnow_naive()
            stop_rule = StopRule(
                application_id=application_id,
                missed_emi_count=missed_count,
                frozen_date=now,
                review_required=True,
                reason=f"{missed_count} EMIs missed or bounced",
            )
            db.add(stop_rule)
            db.commit()

            return StopRuleResult(
                should_freeze=True,
                missed_emi_count=missed_count,
                frozen_date=now,
                review_required=True,
                reason=f"Tranches frozen: {missed_count} EMIs missed (requires officer review)",
            )

        elif should_freeze and existing_stop:
            # Update existing stop rule
            if not existing_stop.frozen_date:
                existing_stop.frozen_date = utcnow_naive()
            existing_stop.missed_emi_count = missed_count
            db.commit()

            return StopRuleResult(
                should_freeze=True,
                missed_emi_count=missed_count,
                frozen_date=existing_stop.frozen_date,
                review_required=existing_stop.review_required,
                reason=f"Tranches frozen: {missed_count} EMIs missed",
            )

        elif not should_freeze and existing_stop and not existing_stop.unfrozen_date:
            # Check if frozen previously, now eligible for unfreezing
            return StopRuleResult(
                should_freeze=False,
                missed_emi_count=missed_count,
                frozen_date=existing_stop.frozen_date,
                review_required=False,
                reason="All EMIs now on schedule, eligible for unfreezing",
            )

        # No freeze needed
        return StopRuleResult(
            should_freeze=False,
            missed_emi_count=missed_count,
            frozen_date=None,
            review_required=False,
            reason="Repayment on track",
        )
