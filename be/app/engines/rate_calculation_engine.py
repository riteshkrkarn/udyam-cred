"""Rate Calculation engine: compute final APR."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.adapters.rate_adapter import RateAdapter


@dataclass
class RateCalculationResult:
    """Result of rate calculation."""

    industry_rate: float
    tier_adjustment: float
    final_rate: float
    rate_date: datetime


class RateCalculationEngine:
    """Calculate final APR from industry rate + tier adjustment."""

    @staticmethod
    def calculate_rate(
        tier: int,
        db: Session,
        rate_date: Optional[datetime] = None,
    ) -> RateCalculationResult:
        """
        Calculate final rate for a tier.

        Args:
            tier: Tier number (1, 2, or 3)
            db: Database session
            rate_date: Specific date to fetch rate for (defaults to latest)

        Returns:
            RateCalculationResult with rate components
        """
        # Tier adjustments
        tier_adjustments = {
            1: 4.0,  # +4%
            2: 2.0,  # +2%
            3: 0.0,  # +0%
        }

        if tier not in {1, 2, 3}:
            return RateCalculationResult(
                industry_rate=0.0,
                tier_adjustment=0.0,
                final_rate=0.0,
                rate_date=datetime.now(),
            )

        # Get industry rate
        industry_rate = RateAdapter.get_industry_rate(tier, db, rate_date)
        tier_adjustment = tier_adjustments[tier]

        # Calculate final rate
        final_rate = industry_rate + tier_adjustment

        return RateCalculationResult(
            industry_rate=industry_rate,
            tier_adjustment=tier_adjustment,
            final_rate=final_rate,
            rate_date=datetime.now(),
        )
