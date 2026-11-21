"""Tranche Plan engine: generate multi-tranche release schedules."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class TrancheDetail:
    """Details of a single tranche."""

    tranche_num: int
    amount: float
    release_date: datetime
    tenor_months: int


@dataclass
class TranchePlanResult:
    """Result of tranche plan generation."""

    tranche_plan: list[TrancheDetail]
    total_amount: float
    tenure_months: int


class TranchePlanEngine:
    """Generate multi-tranche release schedules."""

    @staticmethod
    def generate_plan(
        tier: int,
        amount: float,
        start_date: datetime,
    ) -> TranchePlanResult:
        """
        Generate tranche plan based on tier and amount.

        Args:
            tier: Tier number (1, 2, or 3)
            amount: Total approved amount
            start_date: Date for first tranche release

        Returns:
            TranchePlanResult with tranche schedule
        """
        # Tenure by tier
        tenures = {
            1: 12,
            2: 24,
            3: 36,
        }

        if tier not in {1, 2, 3}:
            return TranchePlanResult(
                tranche_plan=[],
                total_amount=0.0,
                tenure_months=0,
            )

        tenure_months = tenures[tier]
        tranches = []

        if tier == 1:
            # 1 tranche (100% now)
            tranches.append(
                TrancheDetail(
                    tranche_num=1,
                    amount=amount,
                    release_date=start_date,
                    tenor_months=tenure_months,
                )
            )

        elif tier == 2:
            # 2 tranches (60% now, 40% at +60d)
            tranche1_amount = amount * 0.60
            tranche2_amount = amount * 0.40
            tranche2_date = start_date + timedelta(days=60)

            tranches.append(
                TrancheDetail(
                    tranche_num=1,
                    amount=tranche1_amount,
                    release_date=start_date,
                    tenor_months=tenure_months,
                )
            )
            tranches.append(
                TrancheDetail(
                    tranche_num=2,
                    amount=tranche2_amount,
                    release_date=tranche2_date,
                    tenor_months=tenure_months,
                )
            )

        elif tier == 3:
            # 4 tranches (40%, 30%, 20%, 10%)
            tranche1_amount = amount * 0.40
            tranche2_amount = amount * 0.30
            tranche3_amount = amount * 0.20
            tranche4_amount = amount * 0.10

            tranche2_date = start_date + timedelta(days=60)
            tranche3_date = start_date + timedelta(days=120)
            tranche4_date = start_date + timedelta(days=180)

            tranches.append(
                TrancheDetail(
                    tranche_num=1,
                    amount=tranche1_amount,
                    release_date=start_date,
                    tenor_months=tenure_months,
                )
            )
            tranches.append(
                TrancheDetail(
                    tranche_num=2,
                    amount=tranche2_amount,
                    release_date=tranche2_date,
                    tenor_months=tenure_months,
                )
            )
            tranches.append(
                TrancheDetail(
                    tranche_num=3,
                    amount=tranche3_amount,
                    release_date=tranche3_date,
                    tenor_months=tenure_months,
                )
            )
            tranches.append(
                TrancheDetail(
                    tranche_num=4,
                    amount=tranche4_amount,
                    release_date=tranche4_date,
                    tenor_months=tenure_months,
                )
            )

        return TranchePlanResult(
            tranche_plan=tranches,
            total_amount=amount,
            tenure_months=tenure_months,
        )
