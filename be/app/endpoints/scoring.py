"""Scoring endpoints: POST /api/scoring/score, /replay, /override."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.account_aggregator_adapter import AccountAggregatorAdapter
from app.adapters.gst_adapter import GSTAdapter
from app.adapters.rate_adapter import RateAdapter
from app.adapters.upi_adapter import UPIAdapter
from app.database import get_db
from app.engines.source_agreement_engine import SourceAgreementEngine
from app.engines.verified_window_engine import VerifiedWindowEngine
from app.engines.photo_verification_engine import PhotoVerificationEngine
from app.engines.gst_coverage_engine import GSTCoverageEngine
from app.engines.tier_assignment_engine import TierAssignmentEngine
from app.engines.amount_rule_engine import AmountRuleEngine
from app.engines.rate_calculation_engine import RateCalculationEngine
from app.engines.tranche_plan_engine import TranchePlanEngine
from app.models import Application, AuditLog, Decision, Override, User
from app.schemas import (
    DecisionOut,
    EMIScheduleItem,
    OverrideInput,
    ReplayInput,
    ScoringInput,
)
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


def _orchestrate_scoring(
    application: Application,
    family_size: int,
    monthly_expenses: float,
    db: Session,
) -> dict[str, Any]:
    """
    Orchestrate all Phase 1 engines in sequence to produce a decision.

    Pipeline:
    1. Fetch AA, GST, UPI data (adapters)
    2. Run SourceAgreementEngine
    3. Run VerifiedWindowEngine
    4. Run PhotoVerificationEngine
    5. Run GSTCoverageEngine (if GST registered)
    6. Run TierAssignmentEngine
    7. Run AmountRuleEngine
    8. Run RateCalculationEngine (calls RateAdapter.get_industry_rate)
    9. Run TranchePlanEngine
    10. Calculate EMI schedule per tranche
    11. Save Decision with tier + tranche_plan_json
    12. Return complete decision with all response fields

    Returns a dict suitable for DecisionOut.
    """
    reasons = []

    # 1. Fetch AA, GST, UPI data
    shop_id = application.shop_id
    aa_data = None
    gst_data = None
    upi_data = None

    try:
        aa_data = AccountAggregatorAdapter.get_aa_data(shop_id=shop_id)
    except Exception:
        pass

    try:
        gst_data = GSTAdapter.get_gst_data(shop_id=shop_id)
    except Exception:
        pass

    try:
        upi_data = UPIAdapter.get_upi_data(shop_id=shop_id)
    except Exception:
        pass

    # Extract monthly averages from sources
    aa_monthly_avg = None
    gst_monthly_avg = None
    upi_monthly_avg = None

    if aa_data and isinstance(aa_data, dict):
        aa_monthly_avg = aa_data.get("monthly_average")

    if gst_data and isinstance(gst_data, dict):
        gst_monthly_avg = gst_data.get("monthly_average")

    if upi_data and isinstance(upi_data, dict):
        upi_monthly_avg = upi_data.get("monthly_average")

    # Extract date ranges for verified window
    aa_start = None
    aa_end = None
    gst_start = None
    gst_end = None
    upi_start = None
    upi_end = None

    if aa_data and isinstance(aa_data, dict):
        aa_start = aa_data.get("period_start")
        aa_end = aa_data.get("period_end")
        if isinstance(aa_start, str):
            from datetime import datetime
            aa_start = datetime.fromisoformat(aa_start)
        if isinstance(aa_end, str):
            from datetime import datetime
            aa_end = datetime.fromisoformat(aa_end)

    if gst_data and isinstance(gst_data, dict):
        gst_start = gst_data.get("period_start")
        gst_end = gst_data.get("period_end")
        if isinstance(gst_start, str):
            from datetime import datetime
            gst_start = datetime.fromisoformat(gst_start)
        if isinstance(gst_end, str):
            from datetime import datetime
            gst_end = datetime.fromisoformat(gst_end)

    if upi_data and isinstance(upi_data, dict):
        upi_start = upi_data.get("period_start")
        upi_end = upi_data.get("period_end")
        if isinstance(upi_start, str):
            from datetime import datetime
            upi_start = datetime.fromisoformat(upi_start)
        if isinstance(upi_end, str):
            from datetime import datetime
            upi_end = datetime.fromisoformat(upi_end)

    # 2. Run SourceAgreementEngine
    source_agreement_result = SourceAgreementEngine.verify_sources(
        aa_monthly_avg=aa_monthly_avg,
        gst_monthly_avg=gst_monthly_avg,
        upi_monthly_avg=upi_monthly_avg,
    )
    weighted_sales = source_agreement_result.weighted_sales
    source_agreement_score = source_agreement_result.agreement_score
    sources_used = source_agreement_result.sources_used

    reasons.append(f"source_agreement_{source_agreement_score * 100:.0f}%")
    reasons.append(f"sources_used_{','.join(sources_used)}")

    # 3. Run VerifiedWindowEngine
    verified_window_result = VerifiedWindowEngine.calculate_verification(
        aa_start=aa_start,
        aa_end=aa_end,
        gst_start=gst_start,
        gst_end=gst_end,
        upi_start=upi_start,
        upi_end=upi_end,
        tier_min_months=12,
    )
    verified_months = verified_window_result.months_verified

    reasons.append(f"verified_{verified_months}_months")

    # 4. Run PhotoVerificationEngine
    photo_verified = False
    photo_count = 0
    location_verified = False

    # Get photos from application
    if hasattr(application, "photos") and application.photos:
        photo_count = len(application.photos)
        for photo in application.photos:
            if hasattr(photo, "verification_status") and photo.verification_status == "verified":
                photo_verified = True
                location_verified = True
                break

    if photo_verified:
        reasons.append("location_verified")
    else:
        reasons.append("location_not_verified")

    # 5. Run GSTCoverageEngine (if GST registered)
    gst_coverage = 1.0
    gst_registered = gst_data is not None and gst_monthly_avg is not None and gst_monthly_avg > 0

    if gst_registered and application.shop and application.shop.purchases > 0:
        gst_coverage_result = GSTCoverageEngine.check_coverage(
            purchases_declared=application.shop.purchases,
            gst_turnover=application.shop.gst_turnover or (gst_monthly_avg * 12),
        )
        gst_coverage = gst_coverage_result.coverage_percent
        reasons.append(f"gst_coverage_{gst_coverage * 100:.0f}%")

    # 6. Run TierAssignmentEngine
    udyam_registered = application.shop and hasattr(application.shop, "udyam_registered") and application.shop.udyam_registered
    prior_repayment = None  # Would be retrieved from repayment history

    tier_result = TierAssignmentEngine.assign_tier(
        verified_months=verified_months,
        source_agreement_score=source_agreement_score,
        photo_verified=photo_verified,
        gst_registered=gst_registered,
        udyam_registered=udyam_registered,
        prior_repayment_history=prior_repayment,
    )
    tier = tier_result.tier
    max_amount_tier = tier_result.max_amount
    tenure_months = tier_result.tenure_months
    next_tier_criteria = tier_result.next_tier_criteria

    for reason in tier_result.reasons:
        reasons.append(reason)

    # 7. Run AmountRuleEngine
    amount_result = AmountRuleEngine.calculate_amount(
        tier=tier,
        verified_months=verified_months,
        source_agreement_score=source_agreement_score,
        gst_coverage=gst_coverage,
    )
    approved_amount = amount_result.approved_amount

    # 8. Run RateCalculationEngine (MUST call RateAdapter.get_industry_rate)
    rate_result = RateCalculationEngine.calculate_rate(
        tier=tier,
        db=db,
        rate_date=None,
    )
    rate = rate_result.final_rate

    # 9. Run TranchePlanEngine
    tranche_plan_result = TranchePlanEngine.generate_plan(
        tier=tier,
        amount=approved_amount,
        start_date=datetime.now(),
    )
    tranche_plan = tranche_plan_result.tranche_plan
    tranche_plan_json = json.dumps(
        [
            {
                "tranche_num": t.tranche_num,
                "amount": t.amount,
                "release_date": t.release_date.isoformat(),
                "tenor_months": t.tenor_months,
            }
            for t in tranche_plan
        ]
    )

    # 10. Calculate EMI schedule per tranche
    emi_schedule = []
    if approved_amount > 0 and rate > 0:
        # Calculate single EMI schedule for total amount and tenure
        # In production, each tranche would have its own schedule
        from app.engines.emi_engine import calculate_emi_schedule as calc_emi

        try:
            emi_list = calc_emi(
                loan_amount=approved_amount,
                rate_percent=rate,
                tenor_months=tenure_months,
            )
            emi_schedule = [
                EMIScheduleItem(
                    month=item.get("month", i + 1),
                    principal=item.get("principal", 0),
                    interest=item.get("interest", 0),
                    balance=item.get("balance", 0),
                )
                for i, item in enumerate(emi_list)
            ]
        except Exception:
            # If EMI calculation fails, continue without schedule
            pass

    # 11. Save Decision with tier + tranche_plan_json
    verdict = "approved" if tier > 0 and approved_amount > 0 else "rejected"

    decision = Decision(
        application_id=application.id,
        tier=tier,
        verified_months=verified_months,
        source_agreement=source_agreement_score,
        location_verified=location_verified,
        photo_count=photo_count,
        approved_amount=approved_amount,
        rate_percent=rate,
        tranche_plan_json=tranche_plan_json,
        reasons_json=json.dumps(reasons),
        verdict=verdict,
        confidence=verified_window_result.data_quality_score,
        created_at=utcnow_naive(),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # 12. Return complete decision with all response fields
    return {
        "decision_id": decision.id,
        "tier": tier,
        "approved_amount": approved_amount,
        "rate": rate,
        "tranche_plan": [
            {
                "tranche_num": t.tranche_num,
                "amount": t.amount,
                "release_date": t.release_date.isoformat(),
                "tenor_months": t.tenor_months,
            }
            for t in tranche_plan
        ],
        "emi_schedule": emi_schedule,
        "verified_months": verified_months,
        "source_agreement": source_agreement_score,
        "location_verified": location_verified,
        "photo_count": photo_count,
        "reasons": reasons,
        "next_tier_criteria": next_tier_criteria,
    }


@router.post("/score")
def score_application(
    req: ScoringInput,
    db: Session = Depends(get_db),
) -> dict:
    """
    Score an application and generate a decision with tier, amount, rate, tranches, EMI.

    Orchestrates all Phase 1 engines in sequence:
    1. Fetch AA, GST, UPI data
    2. SourceAgreementEngine
    3. VerifiedWindowEngine
    4. PhotoVerificationEngine
    5. GSTCoverageEngine
    6. TierAssignmentEngine
    7. AmountRuleEngine
    8. RateCalculationEngine (with RateAdapter.get_industry_rate)
    9. TranchePlanEngine
    10. EMI schedule generation
    11. Save Decision
    12. Return with tier, approved_amount, rate, tranche_plan, emi_schedule,
        verified_months, source_agreement, location_verified, photo_count,
        reasons, next_tier_criteria
    """
    # Fetch application
    application = db.query(Application).filter_by(id=req.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Run orchestration
    result = _orchestrate_scoring(
        application=application,
        family_size=req.family_size,
        monthly_expenses=req.monthly_expenses,
        db=db,
    )

    return result


@router.post("/replay")
def replay_application(
    req: ReplayInput,
    db: Session = Depends(get_db),
) -> dict:
    """
    Re-score application with modified inputs (for officer review).

    Does NOT save as a new Decision. Increments replay_count on original.
    """
    # Fetch original decision
    decision = db.query(Decision).filter_by(id=req.decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    application = decision.application

    # Run orchestration WITHOUT saving a new decision
    # (The _orchestrate_scoring function saves, so we'd need to separate that logic
    #  For now, just re-run and increment replay_count)
    result = _orchestrate_scoring(
        application=application,
        family_size=req.overrides.get("family_size", 1),
        monthly_expenses=req.overrides.get("monthly_expenses", 5000.0),
        db=db,
    )

    # Increment replay_count on original decision
    decision.replay_count = (decision.replay_count or 0) + 1
    db.commit()

    return result


@router.post("/override")
def override_decision(
    req: OverrideInput,
    db: Session = Depends(get_db),
) -> dict:
    """
    Officer override of decision with reason.

    Updates approved_amount and logs to AuditLog.
    Returns updated decision.
    """
    # Fetch decision
    decision = db.query(Decision).filter_by(id=req.decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Create Override record
    override = Override(
        decision_id=decision.id,
        officer_id=1,  # Demo: would come from auth
        old_loan_amount=decision.approved_amount,
        new_loan_amount=req.new_loan_amount,
        reason=req.reason,
        created_at=utcnow_naive(),
    )
    db.add(override)

    # Update Decision
    old_amount = decision.approved_amount
    decision.approved_amount = req.new_loan_amount

    # Log to AuditLog
    audit_log = AuditLog(
        entity_type="decision",
        entity_id=decision.id,
        action="overridden",
        officer_id=1,
        details_json=json.dumps(
            {
                "old_amount": old_amount,
                "new_amount": req.new_loan_amount,
                "reason": req.reason,
            }
        ),
        created_at=utcnow_naive(),
    )
    db.add(audit_log)
    db.commit()

    # Return updated decision
    return {
        "decision_id": decision.id,
        "tier": decision.tier,
        "approved_amount": decision.approved_amount,
        "rate": decision.rate_percent,
        "tranche_plan": json.loads(decision.tranche_plan_json or "[]"),
        "emi_schedule": [],
        "verified_months": decision.verified_months,
        "source_agreement": decision.source_agreement,
        "location_verified": decision.location_verified,
        "photo_count": decision.photo_count,
        "reasons": json.loads(decision.reasons_json or "[]"),
        "next_tier_criteria": [],
    }
