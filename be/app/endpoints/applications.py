"""Applications endpoints: CRUD for loan applications."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Decision, Override, User
from app.schemas import ApplicationCreateInput, ApplicationOut, ApplicationUpdateInput
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/applications", tags=["applications"])


def get_current_user_mock() -> User | None:
    """Mock user extractor. In production, use Depends(get_current_user) from main."""
    return None


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    req: ApplicationCreateInput,
    current_user: User | None = Depends(get_current_user_mock),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    """Create new application."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # In demo, allow any user. In production, verify borrower role
    application = Application(
        borrower_id=current_user.id,
        shop_id=req.shop_id,
        loan_amount_requested=req.loan_amount_requested,
        purpose=req.purpose,
        status="pending",
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    return ApplicationOut(
        id=application.id,
        borrower_id=application.borrower_id,
        shop_id=application.shop_id,
        loan_amount_requested=application.loan_amount_requested,
        purpose=application.purpose,
        status=application.status,
        created_at=application.created_at.isoformat(),
    )


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    current_user: User | None = Depends(get_current_user_mock),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    """Get application details."""
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Permission check: borrower can only access own; officer/auditor can view all
    if current_user and current_user.role == "borrower" and application.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return ApplicationOut(
        id=application.id,
        borrower_id=application.borrower_id,
        shop_id=application.shop_id,
        loan_amount_requested=application.loan_amount_requested,
        purpose=application.purpose,
        status=application.status,
        created_at=application.created_at.isoformat(),
    )


@router.get("")
def list_applications(
    status: Optional[str] = None,
    current_user: User | None = Depends(get_current_user_mock),
    db: Session = Depends(get_db),
) -> list[ApplicationOut]:
    """
    List applications.

    Filter by status if provided.
    Borrower sees only own applications; officer/auditor see all.
    """
    query = db.query(Application)

    # Permission filter
    if current_user and current_user.role == "borrower":
        query = query.filter_by(borrower_id=current_user.id)

    # Status filter
    if status:
        query = query.filter_by(status=status)

    applications = query.all()

    return [
        ApplicationOut(
            id=app.id,
            borrower_id=app.borrower_id,
            shop_id=app.shop_id,
            loan_amount_requested=app.loan_amount_requested,
            purpose=app.purpose,
            status=app.status,
            created_at=app.created_at.isoformat(),
        )
        for app in applications
    ]


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application_status(
    application_id: int,
    req: ApplicationUpdateInput,
    current_user: User | None = Depends(get_current_user_mock),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    """Update application status."""
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Permission: only officer/auditor or borrower (self) can update
    if current_user and current_user.role == "borrower" and application.borrower_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Validate status
    valid_statuses = {"pending", "submitted", "under_review", "approved", "rejected"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")

    application.status = req.status
    db.commit()
    db.refresh(application)

    return ApplicationOut(
        id=application.id,
        borrower_id=application.borrower_id,
        shop_id=application.shop_id,
        loan_amount_requested=application.loan_amount_requested,
        purpose=application.purpose,
        status=application.status,
        created_at=application.created_at.isoformat(),
    )
