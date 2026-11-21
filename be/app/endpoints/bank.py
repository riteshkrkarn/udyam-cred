"""Bank officer endpoints for queue, case view, decision, and verification console."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, User, VerificationStage

router = APIRouter(prefix="/bank", tags=["bank"])


@router.get("/queue")
def get_application_queue(
    db: Session = Depends(get_db),
    tier: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Get queue of applications for bank officer."""
    query = db.query(Application).filter(Application.status.in_(["verified", "approved", "rejected"]))
    
    if tier:
        # Filter by tier from verification stages
        query = query.join(VerificationStage).filter(VerificationStage.stage_key == "tier_rule")
    
    total = query.count()
    apps = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "applications": [
            {
                "id": app.id,
                "shop_id": app.shop_id,
                "amount_requested": app.loan_amount_requested,
                "status": app.status,
                "created_at": app.created_at.isoformat(),
            }
            for app in apps
        ],
    }


@router.get("/cases/{app_id}")
def get_case_view(app_id: int, db: Session = Depends(get_db)) -> dict:
    """Get case view with all sources and evidence."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    stages = db.query(VerificationStage).filter(
        VerificationStage.application_id == app_id
    ).order_by(VerificationStage.stage_order).all()
    
    # Extract tier and amount
    tier = 1
    amount = app.loan_amount_requested
    confidence = 0.75
    
    for stage in stages:
        if stage.stage_key == "tier_rule":
            outcome = json.loads(stage.outcome_json)
            tier = outcome.get("tier", 1)
        elif stage.stage_key == "amount_rule":
            outcome = json.loads(stage.outcome_json)
            amount = outcome.get("loan_amount", amount)
        elif stage.stage_key == "scoring":
            outcome = json.loads(stage.outcome_json)
            confidence = outcome.get("confidence", 0.75)
    
    return {
        "application_id": app_id,
        "tier": tier,
        "amount": amount,
        "confidence": confidence,
        "status": app.status,
        "photos_count": len(app.photos) if hasattr(app, 'photos') else 0,
        "documents_count": len(app.documents) if hasattr(app, 'documents') else 0,
        "bank_inflows_months": len(app.bank_inflows) if hasattr(app, 'bank_inflows') else 0,
    }


@router.get("/cases/{app_id}/decision")
def get_decision_screen(app_id: int, db: Session = Depends(get_db)) -> dict:
    """Get decision screen with amount, tenor, tranche plan."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    stages = db.query(VerificationStage).filter(
        VerificationStage.application_id == app_id
    ).all()
    
    # Build decision from stages
    tier = 1
    amount = app.loan_amount_requested
    reasons = []
    
    for stage in stages:
        if stage.stage_key == "tier_rule":
            outcome = json.loads(stage.outcome_json)
            tier = outcome.get("tier", 1)
        elif stage.stage_key == "amount_rule":
            outcome = json.loads(stage.outcome_json)
            amount = outcome.get("loan_amount", amount)
        elif stage.stage_key == "scoring":
            outcome = json.loads(stage.outcome_json)
            reasons = outcome.get("reasons", [])
    
    return {
        "tier": tier,
        "amount": amount,
        "tenor_months": 12,
        "rate_percent": 12.0,
        "reasons": reasons,
        "tranche_plan": {
            "tranche_1": {"amount": amount * 0.5, "condition": "On approval"},
            "tranche_2": {"amount": amount * 0.3, "condition": "After 3 on-time EMIs"},
            "tranche_3": {"amount": amount * 0.2, "condition": "After 6 on-time EMIs"},
        },
    }


@router.post("/cases/{app_id}/override")
def override_decision(
    app_id: int,
    reason: str,
    new_amount: Optional[float] = None,
    db: Session = Depends(get_db),
) -> dict:
    """Officer override of automatic decision (requires approver role)."""
    # TODO: Check user role in production
    # if not current_user or current_user.role not in ["approver", "officer"]:
    #     raise HTTPException(status_code=403, detail="Only approvers can override")
    
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # TODO: Create Override record with audit trail
    
    return {"status": "override_recorded", "application_id": app_id}


@router.get("/cases/{app_id}/verification")
def get_verification_console(app_id: int, db: Session = Depends(get_db)) -> dict:
    """Get all 17 stages for verification console."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    stages = db.query(VerificationStage).filter(
        VerificationStage.application_id == app_id
    ).order_by(VerificationStage.stage_order).all()
    
    stage_details = []
    for stage in stages:
        inputs = json.loads(stage.inputs_json)
        outcome = json.loads(stage.outcome_json)
        
        stage_details.append({
            "stage_order": stage.stage_order,
            "stage_key": stage.stage_key,
            "result": stage.result,
            "inputs": inputs,
            "outcome": outcome,
            "rule_version": stage.rule_version,
        })
    
    return {
        "application_id": app_id,
        "stages": stage_details,
        "total_stages": len(stage_details),
    }


@router.get("/loans")
def get_repayment_monitor(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Get repayment monitor across all loans."""
    # TODO: Implement loan queries with EMI status
    return {
        "loans": [],
        "total": 0,
    }


@router.get("/loans/{loan_id}")
def get_loan_details(loan_id: int, db: Session = Depends(get_db)) -> dict:
    """Get one loan with EMI calendar and stop rule status."""
    # TODO: Implement loan detail view
    return {
        "loan_id": loan_id,
        "status": "active",
    }


@router.get("/audit")
def get_audit_log(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Get audit log of decisions and overrides."""
    # TODO: Implement audit log queries
    return {
        "entries": [],
        "total": 0,
    }


@router.get("/fairness")
def get_fairness_analysis(db: Session = Depends(get_db)) -> dict:
    """Get fairness analysis by group (tier, location, family size)."""
    # TODO: Implement fairness calculations
    return {
        "by_tier": {},
        "by_location": {},
        "with_family_size": {},
        "without_family_size": {},
    }
