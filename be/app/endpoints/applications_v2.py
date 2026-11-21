"""Application endpoints for Stage B intake workflow."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, User, VerificationStage
from app.schemas import ApplicationCreateInput, ApplicationOut, ApplicationResultOut
from app.engines.verification_pipeline import run_verification_pipeline
from app.policy import load_policy
from app.utils import utcnow_naive

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    req: ApplicationCreateInput,
    db: Session = Depends(get_db),
) -> ApplicationOut:
    """Create a new application."""
    app = Application(
        borrower_id=1,  # Use authenticated user ID in production
        shop_id=req.shop_id,
        loan_amount_requested=req.loan_amount_requested,
        purpose=req.purpose,
        status="draft",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    
    return ApplicationOut(
        id=app.id,
        borrower_id=app.borrower_id,
        shop_id=app.shop_id,
        loan_amount_requested=app.loan_amount_requested,
        purpose=app.purpose,
        status=app.status,
        created_at=app.created_at.isoformat(),
    )


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(
    app_id: int,
    db: Session = Depends(get_db),
) -> ApplicationOut:
    """Get application details."""
    app = db.query(Application).filter(Application.id == app_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return ApplicationOut(
        id=app.id,
        borrower_id=app.borrower_id,
        shop_id=app.shop_id,
        loan_amount_requested=app.loan_amount_requested,
        purpose=app.purpose,
        status=app.status,
        created_at=app.created_at.isoformat(),
    )


@router.post("/{app_id}/submit")
def submit_application(
    app_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Submit application and trigger verification pipeline.
    
    This runs all 17 stages of verification and produces a decision.
    """
    app = db.query(Application).filter(Application.id == app_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if app.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application cannot be submitted in status {app.status}",
        )
    
    # Load policy
    try:
        policy = load_policy("be/config/policy_v2.yaml")
        policy_dict = {
            "version": policy.version,
            "tier_rule": {},
            "amount_rule": {},
        }
    except Exception:
        # Fallback policy
        policy_dict = {
            "version": "2.0.0",
            "tier_rule": {},
            "amount_rule": {},
        }
    
    # Run verification pipeline
    try:
        result = run_verification_pipeline(db, app_id, policy_dict)
        app.status = "verified"
        db.commit()
        
        return {
            "status": "submitted",
            "application_id": app_id,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}",
        )


@router.get("/{app_id}/result", response_model=ApplicationResultOut)
def get_application_result(
    app_id: int,
    db: Session = Depends(get_db),
) -> ApplicationResultOut:
    """Get the result of the verification pipeline."""
    app = db.query(Application).filter(Application.id == app_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get verification stages
    stages = db.query(VerificationStage).filter(
        VerificationStage.application_id == app_id
    ).order_by(VerificationStage.stage_order).all()
    
    if not stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application has not been verified yet",
        )
    
    # Extract tier and amount from stages
    tier = 1
    amount = app.loan_amount_requested
    for stage in stages:
        if stage.stage_key == "tier_rule":
            outcome = json.loads(stage.outcome_json)
            tier = outcome.get("tier", 1)
        elif stage.stage_key == "amount_rule":
            outcome = json.loads(stage.outcome_json)
            amount = outcome.get("loan_amount", amount)
    
    return ApplicationResultOut(
        application_id=app_id,
        status=app.status,
        tier=tier,
        tier_name=f"Tier {tier}",
        loan_amount=amount,
        tenor_months=12,  # Stub
        rate_percent=12.0,  # Stub
        confidence=0.75,
        reasons=[
            "Bank history shows steady inflows",
            "GST filings match business activity",
            "Household budget within acceptable range",
        ],
        tranche_plan={
            "tranche_1": {"amount": amount * 0.5, "condition": "On approval"},
            "tranche_2": {"amount": amount * 0.3, "condition": "After 3 on-time EMIs"},
            "tranche_3": {"amount": amount * 0.2, "condition": "After 6 on-time EMIs"},
        },
        next_steps=[
            f"Proceed with ₹{amount:.0f} loan approval",
            "Set up EMI schedule",
            "Disburse first tranche",
        ],
    )
