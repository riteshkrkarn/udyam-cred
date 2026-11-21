"""Rate adapter for fetching and storing industry rates by tier."""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import RateEnvironment
from app.utils import utcnow_naive


class RateAdapter:
    """Manage industry rates for tiered lending."""

    # Default fallback rates (in percentage)
    DEFAULT_RATES = {
        1: 14.5,  # Tier 1
        2: 12.0,  # Tier 2
        3: 10.5,  # Tier 3
    }

    @staticmethod
    def get_industry_rate(tier: int, db: Session, rate_date: Optional[datetime] = None) -> float:
        """
        Fetch current industry rate for a given tier.

        Args:
            tier: Tier number (1, 2, or 3)
            db: Database session
            rate_date: Specific date to fetch rate for (defaults to latest)

        Returns:
            Industry rate as a float percentage (e.g., 14.5 for 14.5%)
        """
        if tier not in {1, 2, 3}:
            raise ValueError(f"Invalid tier: {tier}")

        query = db.query(RateEnvironment).order_by(RateEnvironment.rate_date.desc())

        if rate_date:
            query = query.filter(RateEnvironment.rate_date <= rate_date)

        latest = query.first()

        if not latest:
            return RateAdapter.DEFAULT_RATES[tier]

        if tier == 1:
            return latest.tier_1_industry_rate
        elif tier == 2:
            return latest.tier_2_industry_rate
        else:
            return latest.tier_3_industry_rate

    @staticmethod
    def set_industry_rates(
        tier_1: float, tier_2: float, tier_3: float, source: str, db: Session
    ) -> bool:
        """
        Set/update industry rates for all tiers.

        Args:
            tier_1: Industry rate for Tier 1 (percentage)
            tier_2: Industry rate for Tier 2 (percentage)
            tier_3: Industry rate for Tier 3 (percentage)
            source: Source of rates ("manual" or "api")
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        if tier_1 <= 0 or tier_2 <= 0 or tier_3 <= 0:
            return False

        try:
            rate_env = RateEnvironment(
                rate_date=utcnow_naive(),
                tier_1_industry_rate=tier_1,
                tier_2_industry_rate=tier_2,
                tier_3_industry_rate=tier_3,
                source=source,
            )
            db.add(rate_env)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
