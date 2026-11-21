"""Tranche endpoints: list, approve, and check eligibility."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.engines.tranche_rule_engine import TrancheRuleEngine
from app.models import Application, Tranche, RepaymentRecord, AuditLog, User
from app.schemas import TrancheListOut, TrancheDetailsOut, RepaymentStatusOut
from app.utils import utcnow_naive
from app.auth import decode_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/api/applications", tags=["tranches"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Extract current user from JWT token (optional)."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload.get("sub"))
    except Exception:
        return None
    user = db.query(User).filter_by(id=user_id).first()
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract current user from JWT token (required)."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    if not token:
        raise credentials_exc
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id = int(payload.get("sub"))
    except Exception:
        raise credentials_exc
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise credentials_exc
    return user


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


@router.get("/{application_id}/tranches/{tranche_num}/eligibility", status_code=200)
def check_tranche_eligibility(
    application_id: int,
    tranche_num: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    GET /api/applications/{id}/tranches/{tranche_num}/eligibility
    
    Check if a tranche is eligible for release based on repayment history.
    
    Returns:
        {
            "eligible": bool,
            "reason": str,
            "release_date": date or null
        }
    """
    # Verify application exists
    app = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify tranche exists
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

    # Check eligibility using TrancheRuleEngine
    result = TrancheRuleEngine.check_eligibility(
        application_id, tranche_num, db
    )

    # Log the eligibility check for audit
    audit_log = AuditLog(
        entity_type="tranche",
        entity_id=tranche.id,
        action="eligibility_checked",
        officer_id=None,
        details_json=json.dumps({
            "eligible": result.eligible,
            "reason": result.reason,
            "tranche_num": tranche_num,
        }),
        timestamp=utcnow_naive(),
    )
    db.add(audit_log)
    db.commit()

    return {
        "eligible": result.eligible,
        "reason": result.reason,
        "release_date": result.release_date.isoformat() if result.release_date else None,
    }


@router.post("/{application_id}/tranches/{tranche_num}/approve", status_code=200)
def approve_tranche_release(
    application_id: int,
    tranche_num: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    POST /api/applications/{id}/tranches/{tranche_num}/approve
    
    Approve and release a tranche after verifying eligibility.
    
    Actions:
    1. Verify eligibility first using TrancheRuleEngine
    2. If not eligible, return error with reason
    3. If eligible:
       - Set tranche.release_status = "released"
       - Set tranche.release_date = today()
       - Create AuditLog entry with reason and user
       - Save and return tranche details
    
    Returns:
        {
            "tranche_details": {...},
            "release_date": date,
            "audit_entry_id": int
        }
    """
    # Verify application exists
    app = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify tranche exists
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

    # Check if already released
    if tranche.release_status == "released":
        raise HTTPException(status_code=400, detail="Tranche already released")

    if tranche.release_status == "repaid":
        raise HTTPException(status_code=400, detail="Tranche already repaid")

    # Verify eligibility first
    eligible_result = TrancheRuleEngine.check_eligibility(
        application_id, tranche_num, db
    )
    
    if not eligible_result.eligible:
        raise HTTPException(
            status_code=400,
            detail=eligible_result.reason
        )

    # Approve and release the tranche
    release_date = utcnow_naive()
    tranche.release_status = "released"
    tranche.release_date = release_date
    db.flush()

    # Create audit log entry
    audit_log = AuditLog(
        entity_type="tranche",
        entity_id=tranche.id,
        action="approved",
        officer_id=current_user.id,
        details_json=json.dumps({
            "tranche_num": tranche_num,
            "amount": tranche.amount,
            "approved_by": current_user.email,
            "reason": eligible_result.reason,
        }),
        timestamp=release_date,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    # Get repayment records for this tranche
    repayment_records = (
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
        for r in repayment_records
    ]

    return {
        "tranche_details": {
            "id": tranche.id,
            "tranche_num": tranche.tranche_num,
            "amount": tranche.amount,
            "release_date": tranche.release_date.isoformat(),
            "release_status": tranche.release_status,
            "emi_count": tranche.emi_count,
            "tenor_months": tranche.tenor_months,
            "repayment_history": repayment_history,
        },
        "release_date": release_date.isoformat(),
        "audit_entry_id": audit_log.id,
    }

