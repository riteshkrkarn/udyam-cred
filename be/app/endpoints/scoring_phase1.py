"""Phase 1 Scoring endpoint: tiered verification-first scoring."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.rate_adapter import RateAdapter
from app.database import get_db
from app.engines.photo_verification_engine import PhotoVerificationEngine
from app.engines.source_agreement_engine import SourceAgreementEngine
from app.engines.verified_window_engine import VerifiedWindowEngine
from app.engines.gst_coverage_engine import GSTCoverageEngine
from app.engines.tier_assignment_engine import TierAssignmentEngine
from app.engines.amount_rule_engine import AmountRuleEngine
from app.engines.rate_calculation_engine import RateCalculationEngine
from app.engines.tranche_plan_engine import TranchePlanEngine
from app.engines.tranche_rule_engine import TrancheRuleEngine
from app.models import (
    Application,
    Decision,
    Photo,
    SourceAgreement,
    VerifiedWindow,
    GSTCoverage,
    Tranche,
    RepaymentRecord,
    DataSource,
    User,
)
from app.schemas import Phase1DecisionOut, ScoringPhase1Input, TrancheDetailOut, EMIScheduleItem
from app.templates.reasons import (
    generate_plain_reasons,
    generate_next_tier_criteria,
)
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/scoring", tags=["scoring-phase1"])


def calculate_emi_schedule(
    amount: float, monthly_rate: float, months: int
) -> list[EMIScheduleItem]:
    """
    Calculate monthly EMI schedule.

    Args:
        amount: Loan amount
        monthly_rate: Monthly interest rate (annual_rate / 12 / 100)
        months: Tenure in months

    Returns:
        List of EMI schedule items
    """
    if amount <= 0 or months <= 0:
        return []

    # Calculate monthly EMI using standard formula
    monthly_rate_decimal = monthly_rate / 100
    if monthly_rate_decimal == 0:
        emi = amount / months
    else:
        emi = (
            amount
            * monthly_rate_decimal
            * (1 + monthly_rate_decimal) ** months
            / ((1 + monthly_rate_decimal) ** months - 1)
        )

    schedule = []
    balance = amount

    for month in range(1, months + 1):
        interest = balance * monthly_rate_decimal
        principal = emi - interest
        balance -= principal

        schedule.append(
            EMIScheduleItem(
                month=month,
                principal=max(principal, 0),
                interest=interest,
                balance=max(balance, 0),
            )
        )

    return schedule


@router.post("/score", response_model=Phase1DecisionOut)
def score_application(
    req: ScoringPhase1Input,
    db: Session = Depends(get_db),
) -> Phase1DecisionOut:
    """
    Score an application using Phase 1 tiered verification-first system.

    New Logic:
    1. Fetch AA, GST, UPI data
    2. Run Source Agreement Engine
    3. Run Verified Window Engine
    4. Run Photo Verification Engine
    5. Run GST Coverage Engine (if registered)
    6. Run Tier Assignment Engine
    7. Run Amount Rule Engine
    8. Run Rate Calculation Engine
    9. Run Tranche Plan Generator
    10. Calculate EMI per tranche
    11. Save Decision with tier + tranche plan
    12. Return decision
    """
    # Get application
    app = (
        db.query(Application)
        .filter(Application.id == req.application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify consent
    if not req.consent_given:
        raise HTTPException(status_code=400, detail="Consent required")

    reasons = []
    next_tier_criteria = []

    # 1. Fetch data sources
    data_sources = (
        db.query(DataSource)
        .filter(DataSource.application_id == req.application_id)
        .all()
    )

    aa_data = None
    gst_data = None
    upi_data = None

    for ds in data_sources:
        if ds.source == "aa":
            try:
                aa_data = json.loads(ds.data_json)
            except:
                pass
        elif ds.source == "gst":
            try:
                gst_data = json.loads(ds.data_json)
            except:
                pass
        elif ds.source == "upi":
            try:
                upi_data = json.loads(ds.data_json)
            except:
                pass

    # 2. Run Source Agreement Engine
    aa_monthly = aa_data.get("monthly_avg") if aa_data else None
    gst_monthly = gst_data.get("monthly_avg") if gst_data else None
    upi_monthly = upi_data.get("monthly_avg") if upi_data else None

    source_agreement_result = SourceAgreementEngine.verify_sources(
        aa_monthly_avg=aa_monthly,
        gst_monthly_avg=gst_monthly,
        upi_monthly_avg=upi_monthly,
    )

    # Save SourceAgreement record
    existing_sa = (
        db.query(SourceAgreement)
        .filter(SourceAgreement.application_id == req.application_id)
        .first()
    )
    if existing_sa:
        db.delete(existing_sa)

    source_agreement_record = SourceAgreement(
        application_id=req.application_id,
        aa_monthly_avg=aa_monthly,
        gst_monthly_avg=gst_monthly,
        upi_monthly_avg=upi_monthly,
        agreement_score_percent=source_agreement_result.agreement_score,
        weighted_sales=source_agreement_result.weighted_sales,
        sources_used=",".join(source_agreement_result.sources_used),
        confidence=source_agreement_result.confidence,
    )
    db.add(source_agreement_record)

    # 3. Run Verified Window Engine
    aa_start = None
    aa_end = None
    gst_start = None
    gst_end = None
    upi_start = None
    upi_end = None

    if aa_data:
        try:
            aa_start = datetime.fromisoformat(aa_data.get("start_date"))
            aa_end = datetime.fromisoformat(aa_data.get("end_date"))
        except:
            pass

    if gst_data:
        try:
            gst_start = datetime.fromisoformat(gst_data.get("start_date"))
            gst_end = datetime.fromisoformat(gst_data.get("end_date"))
        except:
            pass

    if upi_data:
        try:
            upi_start = datetime.fromisoformat(upi_data.get("start_date"))
            upi_end = datetime.fromisoformat(upi_data.get("end_date"))
        except:
            pass

    verified_window_result = VerifiedWindowEngine.calculate_verification(
        aa_start=aa_start,
        aa_end=aa_end,
        gst_start=gst_start,
        gst_end=gst_end,
        upi_start=upi_start,
        upi_end=upi_end,
        tier_min_months=6,
    )

    # Save VerifiedWindow record
    existing_vw = (
        db.query(VerifiedWindow)
        .filter(VerifiedWindow.application_id == req.application_id)
        .first()
    )
    if existing_vw:
        db.delete(existing_vw)

    verified_window_record = VerifiedWindow(
        application_id=req.application_id,
        start_date=verified_window_result.window_start,
        end_date=verified_window_result.window_end,
        months_verified=verified_window_result.months_verified,
        data_quality_score=verified_window_result.data_quality_score,
        weighted_importance=verified_window_result.weight_factor,
    )
    db.add(verified_window_record)

    # 4. Run Photo Verification Engine
    photos = (
        db.query(Photo)
        .filter(Photo.application_id == req.application_id)
        .all()
    )

    photo_verified = False
    location_verified = False
    photo_count = len(photos)

    for photo in photos:
        if photo.verification_status == "verified":
            photo_verified = True
            location_verified = True
            break

    # 5. Run GST Coverage Engine
    gst_coverage_result = None
    gst_coverage_flag = False

    if gst_data and aa_data:
        purchases = aa_data.get("purchases", 0)
        gst_turnover = gst_data.get("turnover", 0)

        if purchases > 0 and gst_turnover > 0:
            gst_coverage_result = GSTCoverageEngine.check_coverage(purchases, gst_turnover)
            gst_coverage_flag = gst_coverage_result.reconciliation_flag

            # Save GSTCoverage record
            existing_gc = (
                db.query(GSTCoverage)
                .filter(GSTCoverage.application_id == req.application_id)
                .first()
            )
            if existing_gc:
                db.delete(existing_gc)

            gst_coverage_record = GSTCoverage(
                application_id=req.application_id,
                purchases_declared=purchases,
                gst_turnover=gst_turnover,
                coverage_percent=gst_coverage_result.coverage_percent,
                reconciliation_flag=gst_coverage_flag,
                notes=gst_coverage_result.notes,
            )
            db.add(gst_coverage_record)

    # 6. Run Tier Assignment Engine
    gst_registered = gst_data is not None and gst_data.get("gstin_valid", False)
    udyam_registered = False  # TODO: Check from shop/application data

    tier_result = TierAssignmentEngine.assign_tier(
        verified_months=verified_window_result.months_verified,
        source_agreement_score=source_agreement_result.agreement_score,
        photo_verified=photo_verified,
        gst_registered=gst_registered,
        udyam_registered=udyam_registered,
        prior_repayment_history=None,
    )

    # Generate plain-language reasons for borrower
    decision_data = {
        "tier": tier_result.tier,
        "verdict": "approved" if tier_result.tier > 0 else "rejected",
        "verified_months": verified_window_result.months_verified,
        "source_agreement_score": source_agreement_result.agreement_score,
        "photo_verified": photo_verified,
        "location_verified": location_verified,
        "gst_registered": gst_registered,
        "gst_coverage": gst_coverage_result.coverage_percent if gst_coverage_result else 0.0,
        "udyam_registered": udyam_registered,
        "prior_repayment_history": None,
        "sources_used": list(source_agreement_result.sources_used),
    }
    
    reasons = generate_plain_reasons(decision_data)
    next_tier_criteria = generate_next_tier_criteria(decision_data)

    # If rejected
    if tier_result.tier == 0:
        decision = Decision(
            application_id=req.application_id,
            verdict="rejected",
            tier=None,
            verified_months=verified_window_result.months_verified,
            source_agreement_score=source_agreement_result.agreement_score,
            location_verified=location_verified,
            photo_count=photo_count,
            tranche_plan_json=json.dumps([]),
            reasons_json=json.dumps(reasons),
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        return Phase1DecisionOut(
            decision_id=decision.id,
            verdict="rejected",
            tier=None,
            approved_amount=0.0,
            rate_percent=None,
            tranche_plan=[],
            emi_schedule=[],
            verified_months=verified_window_result.months_verified,
            source_agreement_score=source_agreement_result.agreement_score,
            location_verified=location_verified,
            photo_count=photo_count,
            reasons=reasons,
            next_tier_criteria=next_tier_criteria,
        )

    # 7. Run Amount Rule Engine
    gst_coverage = 1.0
    if gst_coverage_result:
        gst_coverage = gst_coverage_result.coverage_percent

    amount_result = AmountRuleEngine.calculate_amount(
        tier=tier_result.tier,
        verified_months=verified_window_result.months_verified,
        source_agreement_score=source_agreement_result.agreement_score,
        gst_coverage=gst_coverage,
    )

    # 8. Run Rate Calculation Engine
    rate_result = RateCalculationEngine.calculate_rate(
        tier=tier_result.tier,
        db=db,
    )

    # 9. Run Tranche Plan Generator
    tranche_plan_result = TranchePlanEngine.generate_plan(
        tier=tier_result.tier,
        amount=amount_result.approved_amount,
        start_date=utcnow_naive(),
    )

    # 10. Calculate EMI per tranche
    monthly_rate = rate_result.final_rate / 12
    emi_schedule = calculate_emi_schedule(
        amount=amount_result.approved_amount,
        monthly_rate=monthly_rate,
        months=tier_result.tenure_months,
    )

    # 11. Save tranches and create repayment records
    for tranche_detail in tranche_plan_result.tranche_plan:
        tranche = Tranche(
            application_id=req.application_id,
            tranche_num=tranche_detail.tranche_num,
            amount=tranche_detail.amount,
            release_date=tranche_detail.release_date,
            release_status="pending",
            emi_count=tranche_detail.tenor_months,
            tenor_months=tranche_detail.tenor_months,
        )
        db.add(tranche)
        db.flush()

        # Create EMI records for this tranche
        emi_amount = tranche_detail.amount / tranche_detail.tenor_months
        for month in range(1, tranche_detail.tenor_months + 1):
            due_date = tranche_detail.release_date + timedelta(days=30 * month)
            repayment = RepaymentRecord(
                tranche_id=tranche.id,
                emi_num=month,
                due_date=due_date,
                amount=emi_amount,
                payment_status="pending",
                days_late=0,
            )
            db.add(repayment)

    # 12. Save Decision
    tranche_plan_json = [
        {
            "tranche_num": t.tranche_num,
            "amount": t.amount,
            "release_date": t.release_date.isoformat(),
            "tenor_months": t.tenor_months,
        }
        for t in tranche_plan_result.tranche_plan
    ]

    decision = Decision(
        application_id=req.application_id,
        verdict="approved",
        tier=tier_result.tier,
        verified_months=verified_window_result.months_verified,
        source_agreement_score=source_agreement_result.agreement_score,
        location_verified=location_verified,
        photo_count=photo_count,
        tranche_plan_json=json.dumps(tranche_plan_json),
        reasons_json=json.dumps(reasons),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # Return response
    tranche_details = [
        TrancheDetailOut(
            tranche_num=t["tranche_num"],
            amount=t["amount"],
            release_date=t["release_date"],
            tenor_months=t["tenor_months"],
        )
        for t in tranche_plan_json
    ]

    return Phase1DecisionOut(
        decision_id=decision.id,
        verdict="approved",
        tier=tier_result.tier,
        approved_amount=amount_result.approved_amount,
        rate_percent=rate_result.final_rate,
        tranche_plan=tranche_details,
        emi_schedule=emi_schedule,
        verified_months=verified_window_result.months_verified,
        source_agreement_score=source_agreement_result.agreement_score,
        location_verified=location_verified,
        photo_count=photo_count,
        reasons=reasons,
        next_tier_criteria=next_tier_criteria,
    )
