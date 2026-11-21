"""Audit endpoints: decision and override audit trail."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Decision, Override, User
from app.schemas import DecisionAuditOut, OverrideOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


def get_current_user_mock() -> User | None:
    """Mock user extractor. In production, use Depends(get_current_user)."""
    return None


@router.get("/decisions", response_model=list[DecisionAuditOut])
def list_decisions_audit(
    application_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User | None = Depends(get_current_user_mock),
    db: Session = Depends(get_db),
) -> list[DecisionAuditOut]:
    """
    List all decisions with full audit trail.

    Filters by application_id, date range if provided.
    Permissions: officer/auditor only.
    
    Returns: [{decision_id, application_id, verdict, loan_amount, replay_count, 
              overrides: [...], created_at}, ...]
    """
    # Permission check: officer/auditor only
    if current_user and current_user.role not in {"officer", "approver", "auditor"}:
        raise HTTPException(status_code=403, detail="Officer or auditor role required")

    # Build query
    query = db.query(Decision)

    # Filter by application_id if provided
    if application_id:
        query = query.filter(Decision.application_id == application_id)

    # Filter by date range if provided
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
            query = query.filter(Decision.created_at >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
            query = query.filter(Decision.created_at <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")

    decisions = query.all()

    result = []
    for decision in decisions:
        # Fetch overrides for this decision
        overrides_list = db.query(Override).filter(Override.decision_id == decision.id).all()
        
        overrides_out = [
            OverrideOut(
                id=override.id,
                officer_id=override.officer_id,
                old_loan_amount=override.old_loan_amount,
                new_loan_amount=override.new_loan_amount,
                reason=override.reason,
                created_at=override.created_at.isoformat(),
            )
            for override in overrides_list
        ]

        audit_item = DecisionAuditOut(
            decision_id=decision.id,
            application_id=decision.application_id,
            verdict=decision.verdict,
            loan_amount=decision.loan_amount,
            replay_count=decision.replay_count,
            overrides=overrides_out,
            created_at=decision.created_at.isoformat(),
        )
        result.append(audit_item)

    return result
