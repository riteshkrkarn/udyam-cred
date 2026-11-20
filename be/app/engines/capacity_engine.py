"""Capacity Engine - Predict safe repayment amount using trained model or fallback."""
from typing import Any, Optional
import os
import pickle
import logging

logger = logging.getLogger(__name__)


def get_safe_amount(
    goods_sold: float,
    margin: float,
    family_size: int,
    liabilities: float,
    round_trip_score: float,
    vintage_months: int,
    abca: Optional[float] = None,
) -> dict[str, Any]:
    """
    Predict safe repayment amount using trained model or fallback rule.

    Args:
        goods_sold: Estimated goods sold
        margin: Profit margin percentage (0-100)
        family_size: Number of household members
        liabilities: Existing liabilities
        round_trip_score: Round-trip detection score (0-1)
        vintage_months: Number of months of data available
        abca: ABCA value for fallback calculation

    Returns:
        {
            safe_amount: float - Recommended safe loan amount
            confidence: float - 0.6 (fallback) or 0.8 (model)
            capacity_used_percent: float - Percentage of capacity used
        }
    """
    confidence = 0.0
    capacity_used_percent = 0.0

    # Try to load model
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "ml", "model.pkl"
    )
    model = None

    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            logger.info("Loaded capacity model from ml/model.pkl")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}. Using fallback rule.")
            model = None

    # Use model if available
    if model:
        try:
            # Prepare features for model
            features = {
                "goods_sold": goods_sold,
                "margin": margin,
                "family_size": family_size,
                "liabilities": liabilities,
                "round_trip_score": round_trip_score,
                "vintage_months": vintage_months,
            }
            # Try to predict (model interface may vary)
            if hasattr(model, "predict"):
                safe_amount = float(model.predict([list(features.values())])[0])
            else:
                safe_amount = 0.0
            confidence = 0.8
        except Exception as e:
            logger.warning(f"Model prediction failed: {e}. Using fallback.")
            safe_amount = _fallback_safe_amount(
                abca, goods_sold, margin, round_trip_score
            )
            confidence = 0.6
    else:
        # Use fallback rule
        safe_amount = _fallback_safe_amount(
            abca, goods_sold, margin, round_trip_score
        )
        confidence = 0.6

    # Ensure non-negative and bounded
    safe_amount = max(0.0, min(safe_amount, 500000.0))

    return {
        "safe_amount": safe_amount,
        "confidence": confidence,
        "capacity_used_percent": capacity_used_percent,
    }


def _fallback_safe_amount(
    abca: Optional[float],
    goods_sold: float,
    margin: float,
    round_trip_score: float,
) -> float:
    """
    Fallback rule for safe amount when model unavailable.

    safe_amount = ABCA * 0.5 * (1 - round_trip_score * 0.3)
    If ABCA unavailable, estimate from goods_sold.
    """
    if abca is None or abca <= 0:
        # Estimate ABCA from goods sold
        if goods_sold > 0 and margin > 0:
            cost = goods_sold / (1 - margin / 100.0) if margin < 100 else goods_sold
            abca = cost * 0.6  # Conservative estimate
        else:
            abca = 0.0

    # Apply round-trip risk penalty
    risk_factor = 1.0 - (round_trip_score * 0.3)
    safe_amount = abca * 0.5 * risk_factor

    return max(0.0, safe_amount)
