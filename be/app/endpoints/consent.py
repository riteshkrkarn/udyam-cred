"""Consent endpoints: borrower consent management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Consent
from app.schemas import ConsentInput, ConsentOut
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/applications", tags=["consent"])


@router.post("/{application_id}/consent", response_model=ConsentOut, status_code=201)
def create_consent(
    application_id: int,
    req: ConsentInput,
    db: Session = Depends(get_db),
) -> ConsentOut:
    """
    Create consent record.

    Sets borrower_agreed=True, agreed_at=now, marks application status='consent_received'.
    """
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create or update consent
    consent = (
        db.query(Consent).filter_by(application_id=application_id).first()
        or Consent(application_id=application_id)
    )

    consent.text = req.consent_text
    consent.borrower_agreed = req.agreed
    if req.agreed:
        consent.agreed_at = utcnow_naive()

    db.add(consent)
    
    # Mark application as consent received
    if req.agreed:
        application.status = "consent_received"

    db.commit()
    db.refresh(consent)

    return ConsentOut(
        id=consent.id,
        application_id=consent.application_id,
        borrower_agreed=consent.borrower_agreed,
        agreed_at=consent.agreed_at.isoformat() if consent.agreed_at else None,
        withdrawn_at=consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
    )


@router.delete("/{application_id}/consent")
def withdraw_consent(
    application_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Withdraw consent.

    Sets withdrawn_at=now.
    """
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    consent = db.query(Consent).filter_by(application_id=application_id).first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")

    consent.withdrawn_at = utcnow_naive()
    db.commit()

    return {"withdrawn": True, "withdrawn_at": consent.withdrawn_at.isoformat()}
