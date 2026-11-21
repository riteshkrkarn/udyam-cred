"""Household endpoints: family budget and surplus calculation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, HouseholdData
from app.schemas import HouseholdDataInput, HouseholdDataOut
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/applications", tags=["household"])


@router.post("/{application_id}/household", response_model=HouseholdDataOut)
def create_or_update_household(
    application_id: int,
    req: HouseholdDataInput,
    db: Session = Depends(get_db),
) -> HouseholdDataOut:
    """
    Create/update household data.

    Validates: family_size > 0, monthly_expenses > 0, liabilities >= 0.
    Calculates surplus and returns it.
    """
    # Check application exists
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate input
    if req.family_size <= 0:
        raise HTTPException(status_code=400, detail="family_size must be > 0")
    if req.monthly_expenses <= 0:
        raise HTTPException(status_code=400, detail="monthly_expenses must be > 0")
    if req.liabilities < 0:
        raise HTTPException(status_code=400, detail="liabilities must be >= 0")

    # Create or update
    household = (
        db.query(HouseholdData).filter_by(application_id=application_id).first()
        or HouseholdData(application_id=application_id)
    )

    household.family_size = req.family_size
    household.dependents = req.dependents
    household.monthly_expenses = req.monthly_expenses
    household.assets = req.assets
    household.liabilities = req.liabilities

    db.add(household)
    db.commit()
    db.refresh(household)

    return HouseholdDataOut(
        id=household.id,
        application_id=household.application_id,
        family_size=household.family_size,
        dependents=household.dependents,
        monthly_expenses=household.monthly_expenses,
        assets=household.assets,
        liabilities=household.liabilities,
        created_at=household.created_at.isoformat(),
    )


@router.get("/{application_id}/household", response_model=HouseholdDataOut)
def get_household(
    application_id: int,
    db: Session = Depends(get_db),
) -> HouseholdDataOut:
    """Get household data for application."""
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    household = db.query(HouseholdData).filter_by(application_id=application_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household data not found")

    return HouseholdDataOut(
        id=household.id,
        application_id=household.application_id,
        family_size=household.family_size,
        dependents=household.dependents,
        monthly_expenses=household.monthly_expenses,
        assets=household.assets,
        liabilities=household.liabilities,
        created_at=household.created_at.isoformat(),
    )
