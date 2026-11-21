"""Tranche endpoints: list, approve, and check eligibility."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.engines.tranche_rule_engine import TrancheRuleEngine
from app.models import Application, Tranche, RepaymentRecord
from app.schemas import TrancheListOut, TrancheDetailsOut, RepaymentStatusOut
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/applications", tags=["tranches"])


@router.get("/{application_id}/tranches", response_model=list[TrancheListOut])
def list_tranches(
    application_id: int,
    db: Session = Depends(get_db),
) -> list[TrancheListOut]:
    """
    List all tranches for an application.
    """
    # Check if application exists
    app = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    tranches = (
        db.query(Tranche)
        .filter(Tranche.application_id == application_id)
        .order_by(Tranche.tranche_num)
        .all()
    )

    return [
        TrancheListOut(
            id=t.id,
            tranche_num=t.tranche_num,
            amount=t.amount,
            release_date=t.release_date.isoformat(),
            release_status=t.release_status,
            emi_count=t.emi_count,
            tenor_months=t.tenor_months,
        )
        for t in tranches
    ]


@router.get("/{application_id}/tranches/{tranche_num}", response_model=TrancheDetailsOut)
def get_tranche_details(
    application_id: int,
    tranche_num: int,
    db: Session = Depends(get_db),
) -> TrancheDetailsOut:
    """
    Get tranche details with EMI repayment history.
    """
    tranche = (
        db.query(Tranche)
        .filter(
            Tranche.application_id == application_id,
            Tranche.tranche_num == tranche_num,
        )
        .first()
    )
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")

    # Get repayment records
    repayments = (
        db.query(RepaymentRecord)
        .filter(RepaymentRecord.tranche_id == tranche.id)
        .order_by(RepaymentRecord.emi_num)
        .all()
    )

    repayment_history = [
        {
            "emi_num": r.emi_num,
            "due_date": r.due_date.isoformat(),
            "amount": r.amount,
            "paid_date": r.paid_date.isoformat() if r.paid_date else None,
            "payment_status": r.payment_status,
            "days_late": r.days_late,
        }
        for r in repayments
    ]

    return TrancheDetailsOut(
        id=tranche.id,
        tranche_num=tranche.tranche_num,
        amount=tranche.amount,
        release_date=tranche.release_date.isoformat(),
        release_status=tranche.release_status,
        emi_count=tranche.emi_count,
        tenor_months=tranche.tenor_months,
        repayment_history=repayment_history,
    )


@router.post("/{application_id}/tranches/{tranche_num}/approve", status_code=200)
def approve_tranche_release(
    application_id: int,
    tranche_num: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Officer approves tranche release.
    """
    tranche = (
        db.query(Tranche)
        .filter(
            Tranche.application_id == application_id,
            Tranche.tranche_num == tranche_num,
        )
        .first()
    )
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")

    if tranche.release_status == "released":
        raise HTTPException(status_code=400, detail="Tranche already released")

    if tranche.release_status == "repaid":
        raise HTTPException(status_code=400, detail="Tranche already repaid")

    # Check eligibility
    eligible_result = TrancheRuleEngine.check_eligibility(
        application_id, tranche_num, db
    )
    if not eligible_result.eligible:
        raise HTTPException(status_code=400, detail=eligible_result.reason)

    # Approve release
    tranche.release_status = "released"
    db.commit()

    return {
        "success": True,
        "message": f"Tranche {tranche_num} released",
        "amount": tranche.amount,
    }


@router.get("/{application_id}/tranches/{tranche_num}/eligibility", status_code=200)
def check_tranche_eligibility(
    application_id: int,
    tranche_num: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Check if next tranche is eligible for release.
    """
    tranche = (
        db.query(Tranche)
        .filter(
            Tranche.application_id == application_id,
            Tranche.tranche_num == tranche_num,
        )
        .first()
    )
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")

    # Check eligibility
    result = TrancheRuleEngine.check_eligibility(
        application_id, tranche_num, db
    )

    return {
        "eligible": result.eligible,
        "reason": result.reason,
        "release_date": result.release_date.isoformat() if result.release_date else None,
    }
