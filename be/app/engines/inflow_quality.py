"""Inflow quality engine for UdyamCred v2.

Weights bank inflows: steady repeated inflows rated higher than single large inflows.

Logic:
- Calculate coefficient of variation (CV = std_dev / mean)
- Steady inflows (CV <= 0.3) get 1.5x weight
- Single large inflows (>2x average) get 0.6x weight
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import List


@dataclass
class Inflow:
    """Represents one inflow transaction."""
    date: str  # ISO format
    amount: float
    source: str  # aa_sourced | filing_sourced | owner_entered


@dataclass
class InflowQualityInput:
    """Input to inflow quality engine."""
    inflows: List[Inflow]  # All monthly or transaction inflows


@dataclass
class InflowQualityOutput:
    """Output from inflow quality engine."""
    weighted_average: float  # Adjusted average considering quality
    steady_inflow_count: int
    anomaly_count: int
    overall_quality: str  # steady | mixed | anomalous
    weight_multiplier: float  # How much to scale the base amount
    reasoning: str


def evaluate_inflow_quality(input_data: InflowQualityInput, policy: dict) -> InflowQualityOutput:
    """
    Evaluate inflow quality based on steadiness.
    
    Logic:
    - Calculate CV (coefficient of variation)
    - CV <= 0.3 → steady (weight 1.5x)
    - Single large inflow > 2x average → anomaly (weight 0.6x)
    - Otherwise → mixed (weight 1.0x)
    
    Args:
        input_data: InflowQualityInput with list of inflows
        policy: Policy dict with inflow_quality configuration
    
    Returns:
        InflowQualityOutput with quality level, multiplier, and reasoning
    """
    policy_inflow = policy.get("inflow_quality", {})
    steady_cv_threshold = policy_inflow.get("steady_inflow_cv_threshold", 0.3)
    anomaly_multiplier_threshold = policy_inflow.get("anomaly_multiplier_threshold", 2.0)
    steady_weight = policy_inflow.get("steady_inflow_weight_multiplier", 1.5)
    anomaly_weight = policy_inflow.get("anomaly_weight_multiplier", 0.6)
    
    if not input_data.inflows or len(input_data.inflows) < 2:
        # Not enough data to assess quality
        return InflowQualityOutput(
            weighted_average=sum(i.amount for i in input_data.inflows),
            steady_inflow_count=len(input_data.inflows),
            anomaly_count=0,
            overall_quality="insufficient",
            weight_multiplier=1.0,
            reasoning=f"Only {len(input_data.inflows)} inflow(s); quality cannot be assessed"
        )
    
    # Extract amounts
    amounts = [i.amount for i in input_data.inflows]
    mean_inflow = statistics.mean(amounts)
    
    # Calculate CV
    if len(amounts) > 1:
        stdev = statistics.stdev(amounts)
        cv = stdev / mean_inflow if mean_inflow > 0 else 0
    else:
        cv = 0
        stdev = 0
    
    # Count anomalies
    anomaly_count = sum(1 for a in amounts if a > mean_inflow * anomaly_multiplier_threshold)
    steady_inflow_count = len(amounts) - anomaly_count
    
    # Determine quality level and weight
    if cv <= steady_cv_threshold and anomaly_count == 0:
        quality = "steady"
        weight = steady_weight
        reasoning = f"Steady inflows: CV={cv:.2f} (<=0.3), no anomalies. Weight {weight:.1f}x"
    elif anomaly_count > 0:
        quality = "anomalous"
        weight = anomaly_weight
        reasoning = f"Anomalous inflows: {anomaly_count} large inflows (>2x average). Weight {weight:.1f}x"
    else:
        quality = "mixed"
        weight = 1.0
        reasoning = f"Mixed inflows: CV={cv:.2f}, some variation but no clear anomalies. Weight {weight:.1f}x"
    
    weighted_avg = mean_inflow * weight
    
    return InflowQualityOutput(
        weighted_average=weighted_avg,
        steady_inflow_count=steady_inflow_count,
        anomaly_count=anomaly_count,
        overall_quality=quality,
        weight_multiplier=weight,
        reasoning=reasoning
    )
