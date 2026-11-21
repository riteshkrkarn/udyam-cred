"""GST coverage engine for UdyamCred v2.

Calculates what percentage of purchases are matched to GST filings.

Logic:
- Match purchases list to GST filing amounts
- Coverage = matched_purchases / total_purchases
- Higher coverage → higher confidence signal
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Purchase:
    """Represents one purchase transaction."""
    date: str  # ISO format
    amount: float
    supplier_gstin: str | None


@dataclass
class GSTFiling:
    """Represents one GST filing period."""
    period: str  # YYYYMM
    purchases_total: float
    matched_to_filing: bool


@dataclass
class GSTCoverageInput:
    """Input to GST coverage engine."""
    purchases: List[Purchase]
    gst_filings: List[GSTFiling]
    total_purchases: float


@dataclass
class GSTCoverageOutput:
    """Output from GST coverage engine."""
    coverage_percentage: float  # 0.0 to 100.0
    coverage_level: str  # high | medium | low
    matched_amount: float
    unmatched_amount: float
    confidence_impact: float  # 0.4 to 1.0
    reasoning: str


def calculate_gst_coverage(input_data: GSTCoverageInput, policy: dict) -> GSTCoverageOutput:
    """
    Calculate GST filing coverage of purchases.
    
    Logic:
    - Count purchases that have a matching GSTIN and appear in a GST filing
    - Coverage = matched_amount / total_purchases
    - 80%+ → high signal, 50-80% → medium, <50% → low
    
    Args:
        input_data: GSTCoverageInput with purchases and filings
        policy: Policy dict with gst_coverage configuration
    
    Returns:
        GSTCoverageOutput with coverage %, level, and confidence impact
    """
    policy_gst = policy.get("gst_coverage", {})
    thresholds = policy_gst.get("thresholds", {})
    confidence_impacts = policy_gst.get("confidence_impact", {})
    
    if input_data.total_purchases <= 0:
        return GSTCoverageOutput(
            coverage_percentage=0.0,
            coverage_level="low",
            matched_amount=0.0,
            unmatched_amount=0.0,
            confidence_impact=0.4,
            reasoning="No purchases to match"
        )
    
    # Calculate matched amount
    matched_amount = sum(f.purchases_total for f in input_data.gst_filings if f.matched_to_filing)
    unmatched_amount = input_data.total_purchases - matched_amount
    coverage_pct = (matched_amount / input_data.total_purchases) * 100.0
    
    # Determine level
    high_threshold = thresholds.get("high_coverage", 0.80) * 100
    medium_threshold = thresholds.get("medium_coverage", 0.50) * 100
    
    if coverage_pct >= high_threshold:
        coverage_level = "high"
    elif coverage_pct >= medium_threshold:
        coverage_level = "medium"
    else:
        coverage_level = "low"
    
    # Get confidence impact
    confidence_impact = confidence_impacts.get(f"{coverage_level}_coverage", 0.4)
    
    reasoning = f"GST coverage: {coverage_pct:.1f}% ({matched_amount:.0f} matched of {input_data.total_purchases:.0f} total). Level: {coverage_level}. Confidence impact: {confidence_impact:.2f}x"
    
    return GSTCoverageOutput(
        coverage_percentage=coverage_pct,
        coverage_level=coverage_level,
        matched_amount=matched_amount,
        unmatched_amount=unmatched_amount,
        confidence_impact=confidence_impact,
        reasoning=reasoning
    )
