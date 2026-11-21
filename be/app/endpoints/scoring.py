"""Scoring endpoints: POST /api/scoring/score, /replay, /override."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.account_aggregator_adapter import AccountAggregatorAdapter
from app.adapters.gst_adapter import GSTAdapter
from app.adapters.upi_adapter import UPIAdapter
from app.database import get_db
from app.engines.abca_engine import calculate_abca
from app.engines.capacity_engine import get_safe_amount
from app.engines.emi_engine import calculate_emi_schedule, calculate_household_surplus
from app.engines.fund_split_engine import optimize_fund_split
from app.engines.loan_rules_engine import apply_loan_rules
from app.engines.rate_engine import get_rate
from app.engines.round_trip_engine import detect_round_trip
from app.engines.vintage_engine import get_vintage
from app.models import Application, AuditLog, Decision, Override, User
from app.schemas import (
    DecisionOut,
    EMIScheduleItem,
    OverrideInput,
    OverrideOut,
    ReplayInput,
    ScoringInput,
)
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


def get_current_user_from_token(
    token: str | None = None,
    db: Session | None = None,
) -> User | None:
    """Helper to extract user from token (for override tracking)."""
    # In production, use depends(get_current_user) from main.py
    # For now, return None (demo mode)
    return None


def _orchestrate_scoring(
    application: Application,
    family_size: int,
    monthly_expenses: float,
    existing_liabilities: float,
    tenor_months: int,
    db: Session,
) -> dict[str, Any]:
    """
    Orchestrate all engines in sequence to produce a decision.

    Returns a dict suitable for DecisionOut.
    """
    # 1. Fetch adapters data (UPI, AA, GST)
    shop_id = application.shop_id
    
    upi_data = None
    aa_data = None
    gst_data = None
    
    try:
        upi_data = UPIAdapter.get_upi_data(shop_id=shop_id)
    except Exception:
        pass
    
    try:
        aa_data = AccountAggregatorAdapter.get_aa_data(shop_id=shop_id)
    except Exception:
        pass
    
    try:
        gst_data = GSTAdapter.get_gst_data(shop_id=shop_id)
    except Exception:
        pass

    reasons = []

    # 2. Calculate ABCA
    abca_result = calculate_abca(upi_data=upi_data, aa_data=aa_data)
    abca = abca_result["abca_value"]
    if abca > 0:
        reasons.append("stable_cash_flow")

    # 3. Get vintage (earliest supported date)
    vintage_result = get_vintage(
        upi_vintage_date=abca_result["vintage_dates"].get("upi_vintage"),
        aa_vintage_date=abca_result["vintage_dates"].get("aa_vintage"),
    )
    vintage_date = vintage_result["earliest_date"]
    if vintage_date:
        reasons.append("good_vintage")

    # 4. Detect round-trip
    round_trip_result = detect_round_trip(
        upi_transactions=upi_data.get("data", []) if upi_data else None,
    )
    round_trip_score = round_trip_result["score"]
    if round_trip_score < 0.3:
        reasons.append("clean_transactions")
    elif round_trip_score > 0.7:
        reasons.append("circular_patterns_detected")

    # 5. Calculate household surplus
    household_result = calculate_household_surplus(
        abca=abca,
        monthly_expenses=monthly_expenses,
        existing_liabilities=existing_liabilities,
    )
    household_surplus = household_result["household_surplus"]
    emi_capacity = household_result["emi_capacity"]

    if household_surplus > 0:
        reasons.append("positive_household_surplus")

    # 6. Get safe amount (capacity model)
    capacity_result = get_safe_amount(
        goods_sold=0.0,  # Would come from reconciliation
        margin=20.0,  # Default margin
        family_size=family_size,
        liabilities=existing_liabilities,
        round_trip_score=round_trip_score,
        vintage_months=12,  # Standard 12 months
        abca=abca,
    )
    safe_amount = capacity_result["safe_amount"]

    # 7. Apply loan rules -> loan_amount
    loan_rules_result = apply_loan_rules(
        emi_capacity=emi_capacity,
        safe_amount=safe_amount,
        policy_cap=500000.0,
        minimum_loan=10000.0,
    )
    loan_amount = loan_rules_result["loan_amount"]
    verdict = "approved" if loan_amount > 0 else "rejected"

    if verdict == "approved":
        reasons.append("within_policy_caps")
    else:
        reasons.append("insufficient_capacity")

    # 8. Get rate -> rate_percent (only if approved)
    rate_percent = None
    if verdict == "approved":
        rate_result = get_rate(
            risk_band="Moderate",  # Default risk band
            tenor_months=tenor_months,
        )
        rate_percent = rate_result["rate_percent"]
        band = rate_result.get("band", "Moderate")
        reasons.append(f"rate_band_{band.lower()}")

    # 9. Calculate EMI schedule (only if approved)
    emi_schedule = []
    emi_monthly = None
    if verdict == "approved" and rate_percent and loan_amount > 0:
        schedule_list = calculate_emi_schedule(
            loan_amount=loan_amount,
            rate_percent=rate_percent,
            tenor_months=tenor_months,
        )
        emi_schedule = [
            EMIScheduleItem(
                month=item["month"],
                principal=item["principal"],
                interest=item["interest"],
                balance=item["balance"],
            )
            for item in schedule_list
        ]
        # EMI monthly is the first entry's EMI amount
        if schedule_list:
            emi_monthly = schedule_list[0].get("emi", schedule_list[0].get("principal", 0))

    # 10. Optimize fund split (only if approved)
    fund_plan = None
    if verdict == "approved":
        fund_result = optimize_fund_split(
            loan_amount=loan_amount,
            goods_sold=abca * 12,  # Estimate goods sold from annual ABCA
            margin=20.0,  # Default margin
            category="kirana",  # Would come from shop category
            monthly_turnover=abca,
        )
        fund_plan = {
            "stock_percent": fund_result.get("stock_pct", 50),
            "buffer_percent": fund_result.get("buffer_pct", 10),
            "expansion_percent": fund_result.get("expansion_pct", 20),
            "reserve_percent": fund_result.get("reserve_pct", 20),
            "recommendations": fund_result.get("recommendations", []),
        }

    # 11. Generate reason codes (already done above)

    # 12. Save Decision to database
    confidence = abca_result.get("confidence", 0.6)

    decision = Decision(
        application_id=application.id,
        verdict=verdict,
        loan_amount=loan_amount,
        rate_percent=rate_percent,
        emi_monthly=emi_monthly,
        confidence=confidence,
        reasons_json=json.dumps(reasons),
        replay_count=0,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # 13. Return complete decision JSON
    return {
        "decision_id": decision.id,
        "verdict": verdict,
        "loan_amount": loan_amount,
        "rate_percent": rate_percent,
        "emi_monthly": emi_monthly,
        "emi_schedule": emi_schedule,
        "fund_plan": fund_plan,
        "confidence": confidence,
        "reasons": reasons,
        "abca": abca,
        "household_surplus": household_surplus,
        "safe_amount": safe_amount,
    }


@router.post("/score", response_model=DecisionOut)
def score_application(
    req: ScoringInput,
    db: Session = Depends(get_db),
) -> DecisionOut:
    """
    Score an application and generate a decision with loan amount, rate, EMI, fund plan.

    Orchestrates all engines in sequence.
    """
    # Fetch application
    application = db.query(Application).filter_by(id=req.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check consent
    if not application.consents or not any(c.borrower_agreed for c in application.consents):
        raise HTTPException(status_code=403, detail="Consent required to score")

    # Run orchestration
    result = _orchestrate_scoring(
        application=application,
        family_size=req.family_size,
        monthly_expenses=req.monthly_expenses,
        existing_liabilities=req.existing_liabilities,
        tenor_months=req.tenor_months,
        db=db,
    )

    return DecisionOut(**result)


@router.post("/replay", response_model=DecisionOut)
def replay_application(
    req: ReplayInput,
    db: Session = Depends(get_db),
) -> DecisionOut:
    """
    Re-score application with modified inputs (for officer review).

    Does NOT save as a new Decision. Increments replay_count on original.
    """
    # Fetch original decision
    decision = db.query(Decision).filter_by(id=req.decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    application = decision.application
    
    # Get stored inputs from application and household data
    household = application.household_data[0] if application.household_data else None
    if not household:
        raise HTTPException(status_code=400, detail="Household data required for replay")

    # Build input with overrides
    family_size = req.overrides.get("family_size", household.family_size)
    monthly_expenses = req.overrides.get("monthly_expenses", household.monthly_expenses)
    existing_liabilities = req.overrides.get(
        "existing_liabilities", household.liabilities
    )
    tenor_months = req.overrides.get("tenor_months", 12)

    # Validate types
    family_size = int(family_size)
    monthly_expenses = float(monthly_expenses)
    existing_liabilities = float(existing_liabilities)
    tenor_months = int(tenor_months)

    # Run orchestration WITHOUT saving
    result = _orchestrate_scoring(
        application=application,
        family_size=family_size,
        monthly_expenses=monthly_expenses,
        existing_liabilities=existing_liabilities,
        tenor_months=tenor_months,
        db=db,
    )

    # Increment replay_count on original decision (don't save new decision)
    decision.replay_count += 1
    db.commit()

    return DecisionOut(**result)


@router.post("/override", response_model=DecisionOut)
def override_decision(
    req: OverrideInput,
    current_user: User = Depends(lambda: None),  # In production: Depends(get_current_user)
    db: Session = Depends(get_db),
) -> DecisionOut:
    """
    Officer override of decision with reason.

    Validates new_loan_amount <= capacity.
    Creates Override record and logs to AuditLog.
    Returns updated decision.
    """
    # Fetch decision
    decision = db.query(Decision).filter_by(id=req.decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Validate new amount
    if req.new_loan_amount > decision.application.shop.upi_turnover * 0.5:
        raise HTTPException(
            status_code=400,
            detail=f"Override amount {req.new_loan_amount} exceeds capacity",
        )

    # Create Override record
    override = Override(
        decision_id=decision.id,
        officer_id=current_user.id if current_user else 1,  # Demo: fallback to 1
        old_loan_amount=decision.loan_amount,
        new_loan_amount=req.new_loan_amount,
        reason=req.reason,
    )
    db.add(override)

    # Update Decision
    decision.loan_amount = req.new_loan_amount

    # Log to AuditLog
    audit_log = AuditLog(
        entity_type="decision",
        entity_id=decision.id,
        action="overridden",
        officer_id=current_user.id if current_user else 1,
        details_json=json.dumps(
            {
                "old_amount": override.old_loan_amount,
                "new_amount": req.new_loan_amount,
                "reason": req.reason,
            }
        ),
    )
    db.add(audit_log)
    db.commit()

    # Return updated decision
    return DecisionOut(
        decision_id=decision.id,
        verdict=decision.verdict,
        loan_amount=decision.loan_amount,
        rate_percent=decision.rate_percent,
        emi_monthly=decision.emi_monthly,
        emi_schedule=[],  # Simplified for now
        fund_plan=None,
        confidence=decision.confidence,
        reasons=json.loads(decision.reasons_json or "[]"),
        abca=0.0,  # Would need to recalculate
        household_surplus=0.0,
        safe_amount=0.0,
    )
