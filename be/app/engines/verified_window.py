"""Verified window engine for UdyamCred v2.

Calculates the verified data window (in months) and weighting based on history length.

Logic:
- Minimum 6 months of verified data required for Tier 2 and 3
- Longer history gets higher weight (confidence multiplier)
- 6 months → 1.0x, 12 months → 1.2x, 24 months → 1.5x
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class DataPoint:
    """Represents one data point (e.g., one month of bank inflows)."""
    date: datetime
    source: str  # aa_sourced | filing_sourced | live_capture | owner_entered


@dataclass
class VerifiedWindowInput:
    """Input to verified window engine."""
    data_points: List[DataPoint]  # All verified data points (chronological)
    tier: int = 1


@dataclass
class VerifiedWindowOutput:
    """Output from verified window engine."""
    months_covered: int  # How many months of data?
    weight_multiplier: float  # 1.0 to 1.5x based on history length
    passes_minimum_requirement: bool  # For Tier 2/3, must be >= 6 months
    earliest_date: Optional[datetime]
    latest_date: Optional[datetime]
    reasoning: str


def calculate_verified_window(input_data: VerifiedWindowInput, policy: dict) -> VerifiedWindowOutput:
    """
    Calculate verified data window and weight.
    
    Logic:
    - Count months from earliest to latest data point
    - Higher history length → higher weight multiplier
    - Tier 2/3 require minimum 6 months
    
    Args:
        input_data: VerifiedWindowInput with data points and tier
        policy: Policy dict with verified_window configuration
    
    Returns:
        VerifiedWindowOutput with months, weight, pass/fail, and reasoning
    """
    policy_window = policy.get("verified_window", {})
    min_months_required = policy_window.get("minimum_months_required", 6)
    weighting_rules = policy_window.get("weighting", [])
    
    if not input_data.data_points:
        return VerifiedWindowOutput(
            months_covered=0,
            weight_multiplier=0.0,
            passes_minimum_requirement=False,
            earliest_date=None,
            latest_date=None,
            reasoning="No verified data available"
        )
    
    # Sort data points by date
    sorted_points = sorted(input_data.data_points, key=lambda p: p.date)
    earliest = sorted_points[0].date
    latest = sorted_points[-1].date
    
    # Calculate months covered (approximate, using 30-day months)
    delta_days = (latest - earliest).days
    months_covered = max(1, delta_days // 30)  # At least 1 month if same day
    
    # Find weight multiplier based on months covered
    multiplier = 1.0  # Default
    for rule in weighting_rules:
        if months_covered >= rule.get("months_covered", 0):
            multiplier = max(multiplier, rule.get("weight_multiplier", 1.0))
    
    # Check if meets minimum for tier
    passes_minimum = months_covered >= min_months_required if input_data.tier >= 2 else True
    
    reasoning = f"Verified data covers {months_covered} months (from {earliest.date()} to {latest.date()}), weight multiplier {multiplier:.1f}x"
    if input_data.tier >= 2 and not passes_minimum:
        reasoning += f". Below minimum of {min_months_required} months for Tier {input_data.tier} (tier assignment may be affected)"
    
    return VerifiedWindowOutput(
        months_covered=months_covered,
        weight_multiplier=multiplier,
        passes_minimum_requirement=passes_minimum,
        earliest_date=earliest,
        latest_date=latest,
        reasoning=reasoning
    )
