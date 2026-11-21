"""ABCA (Source Agreement) engine for UdyamCred v2.

Compares monthly sales estimates from different sources:
- A: Bank inflows (AA-sourced)
- B: GST-derived estimates
- C: Combined (bank + GST)
- A: Alt (ledger or photo-derived)

Outputs agreement score and confidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class MonthlyEstimate:
    """Estimate of monthly sales from one source."""
    source: str  # aa_sourced | filing_sourced | ledger_sourced | photo_sourced
    month: str  # YYYYMM
    amount: float


@dataclass
class ABCAInput:
    """Input to ABCA engine."""
    estimates: List[MonthlyEstimate]


@dataclass
class ABCAOutput:
    """Output from ABCA engine."""
    agreement_score: float  # 0.0 to 1.0
    agreement_band: str  # excellent | good | fair | poor | disagree
    confidence: float  # 0.1 to 0.95
    average_gap_pct: float  # Average % gap between estimates
    pairwise_agreement: List[Tuple[str, str, float]]  # (source1, source2, agreement%)
    reasoning: str


def calculate_source_agreement(input_data: ABCAInput, policy: dict) -> ABCAOutput:
    """
    Calculate source agreement (ABCA).
    
    Logic:
    - Group estimates by month
    - For each month, calculate % difference between sources
    - Excellent: >=95% match, Good: 90-95%, Fair: 80-90%, Poor: 60-80%, Disagree: <60%
    - Confidence varies by band
    
    Args:
        input_data: ABCAInput with monthly estimates from different sources
        policy: Policy dict with abca configuration
    
    Returns:
        ABCAOutput with agreement score, band, confidence, and details
    """
    policy_abca = policy.get("abca", {})
    bands = policy_abca.get("agreement_bands", [])
    
    if not input_data.estimates:
        return ABCAOutput(
            agreement_score=0.0,
            agreement_band="disagree",
            confidence=0.1,
            average_gap_pct=100.0,
            pairwise_agreement=[],
            reasoning="No estimates to compare"
        )
    
    # Group by month
    monthly_data: Dict[str, Dict[str, float]] = {}
    for est in input_data.estimates:
        if est.month not in monthly_data:
            monthly_data[est.month] = {}
        monthly_data[est.month][est.source] = est.amount
    
    # Calculate agreement for each month
    pairwise_agreements = []
    all_gaps = []
    
    for month in sorted(monthly_data.keys()):
        sources_data = monthly_data[month]
        sources = sorted(sources_data.keys())
        
        # Compare each pair
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                source1 = sources[i]
                source2 = sources[j]
                amt1 = sources_data[source1]
                amt2 = sources_data[source2]
                
                # Calculate % difference
                max_amt = max(amt1, amt2)
                if max_amt > 0:
                    pct_match = 100.0 * (1.0 - abs(amt1 - amt2) / max_amt)
                else:
                    pct_match = 100.0
                
                pairwise_agreements.append((source1, source2, pct_match))
                all_gaps.append(100.0 - pct_match)
    
    if not all_gaps:
        # Only one source, no comparisons possible
        return ABCAOutput(
            agreement_score=0.5,
            agreement_band="fair",
            confidence=0.6,
            average_gap_pct=0.0,
            pairwise_agreement=pairwise_agreements,
            reasoning="Only one data source available; no cross-source agreement possible"
        )
    
    # Calculate average match percentage
    avg_match_pct = 100.0 - (sum(all_gaps) / len(all_gaps))
    avg_match_decimal = avg_match_pct / 100.0
    
    # Find agreement band
    agreement_band = "disagree"
    confidence = 0.1
    
    for band in bands:
        min_pct = band.get("min_pct_agree", 0.0)
        max_pct = band.get("max_pct_agree", 1.0)
        if min_pct <= avg_match_decimal <= max_pct:
            agreement_band = band.get("band_name", "poor")
            confidence = band.get("confidence", 0.5)
            break
    
    reasoning = f"Source agreement: average {avg_match_pct:.1f}% match across {len(sources_data)} sources over {len(monthly_data)} months. Band: {agreement_band}. Confidence: {confidence:.2f}"
    
    return ABCAOutput(
        agreement_score=avg_match_decimal,
        agreement_band=agreement_band,
        confidence=confidence,
        average_gap_pct=100.0 - avg_match_pct,
        pairwise_agreement=pairwise_agreements,
        reasoning=reasoning
    )
