"""Rate Calculation engine: compute final APR."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.adapters.rate_adapter import RateAdapter

logger = logging.getLogger(__name__)


@dataclass
class RateCalculationResult:
    """Result of rate calculation."""

    industry_rate: float
    tier_adjustment: float
    final_rate: float
    rate_date: datetime


class RateCalculationEngine:
    """Calculate final APR from industry rate + tier adjustment."""

    # Tier adjustments (policy-based adjustments added to industry rate)
    TIER_ADJUSTMENTS = {
        1: 4.0,  # +4%
        2: 2.0,  # +2%
        3: 0.0,  # +0%
    }

    @staticmethod
    def calculate_rate(
        tier: int,
        db: Session,
        rate_date: Optional[datetime] = None,
    ) -> RateCalculationResult:
        """
        Calculate final rate for a tier.

        Fetches the base industry rate via RateAdapter, applies tier-based policy
        adjustment, and logs the calculation for audit trail.

        Args:
            tier: Tier number (1, 2, or 3)
            db: Database session
            rate_date: Specific date to fetch rate for (defaults to latest)

        Returns:
            RateCalculationResult with rate components
        """
        if tier not in {1, 2, 3}:
            logger.warning(f"Invalid tier requested for rate calculation: {tier}")
            return RateCalculationResult(
                industry_rate=0.0,
                tier_adjustment=0.0,
                final_rate=0.0,
                rate_date=datetime.now(),
            )

        # Fetch base industry rate from adapter
        industry_rate = RateAdapter.get_industry_rate(tier, db, rate_date)
        tier_adjustment = RateCalculationEngine.TIER_ADJUSTMENTS[tier]

        # Calculate final rate: base + adjustment
        final_rate = industry_rate + tier_adjustment

        # Log rate fetch and calculation for audit trail
        logger.info(
            f"Rate calculation: tier={tier}, base_rate={industry_rate}%, "
            f"adjustment={tier_adjustment}%, final_rate={final_rate}%"
        )

        return RateCalculationResult(
            industry_rate=industry_rate,
            tier_adjustment=tier_adjustment,
            final_rate=final_rate,
            rate_date=datetime.now(),
        )
