"""Repayment endpoints: view EMI history, record payments, monitor status."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Tranche, RepaymentRecord, User, Decision
from app.schemas import RepaymentStatusOut, NextEMIOut, RepaymentMonitorOut
from app.utils import utcnow_naive
from datetime import datetime

router = APIRouter(prefix="/api/applications", tags=["repayment"])


@router.get("/{application_id}/repayment", response_model=list[RepaymentStatusOut])
def view_repayment_history(
    application_id: int,
    db: Session = Depends(get_db),
) -> list[RepaymentStatusOut]:
    """
    View complete EMI payment history for an application.
    """
    # Check if application exists
    app = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get all tranches and their repayment records
    tranches = (
        db.query(Tranche)
        .filter(Tranche.application_id == application_id)
        .order_by(Tranche.tranche_num)
        .all()
    )

    repayments = []
    for tranche in tranches:
        records = (
            db.query(RepaymentRecord)
            .filter(RepaymentRecord.tranche_id == tranche.id)
            .order_by(RepaymentRecord.emi_num)
            .all()
        )

        for record in records:
            repayments.append(
                RepaymentStatusOut(
                    tranche_num=tranche.tranche_num,
                    emi_num=record.emi_num,
                    due_date=record.due_date.isoformat(),
                    amount=record.amount,
                    paid_date=record.paid_date.isoformat() if record.paid_date else None,
                    payment_status=record.payment_status,
                    days_late=record.days_late,
                )
            )

    return repayments


@router.post("/{application_id}/repayment/record", status_code=201)
def record_emi_payment(
    application_id: int,
    tranche_num: int,
    emi_num: int,
    paid_amount: float,
    paid_date: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """
    Record an EMI payment (admin endpoint).

    Args:
        application_id: Application ID
        tranche_num: Tranche number
        emi_num: EMI number
        paid_amount: Amount paid
        paid_date: Payment date (ISO format, defaults to now)
    """
    # Get tranche
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

    # Get repayment record
    record = (
        db.query(RepaymentRecord)
        .filter(
            RepaymentRecord.tranche_id == tranche.id,
            RepaymentRecord.emi_num == emi_num,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="EMI record not found")

    # Parse payment date
    if paid_date:
        try:
            payment_date = datetime.fromisoformat(paid_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        payment_date = utcnow_naive()

    # Determine payment status
    days_overdue = (payment_date - record.due_date).days
    if days_overdue < 0:
        status_str = "ontime"
        days_late = 0
    elif days_overdue == 0:
        status_str = "ontime"
        days_late = 0
    else:
        status_str = "late"
        days_late = days_overdue

    # Update record
    record.paid_date = payment_date
    record.payment_status = status_str
    record.days_late = days_late

    db.commit()

    return {
        "success": True,
        "message": f"EMI {emi_num} for tranche {tranche_num} recorded",
        "payment_status": status_str,
        "days_late": days_late,
    }


@router.get("/{application_id}/repayment/next-emi", response_model=NextEMIOut | None)
def get_next_emi_due(
    application_id: int,
    db: Session = Depends(get_db),
) -> NextEMIOut | None:
    """
    Get the next EMI due for an application.
    """
    # Get all tranches
    tranches = (
        db.query(Tranche)
        .filter(Tranche.application_id == application_id)
        .order_by(Tranche.tranche_num)
        .all()
    )

    if not tranches:
        return None

    # Find the next pending/overdue EMI
    for tranche in tranches:
        records = (
            db.query(RepaymentRecord)
            .filter(RepaymentRecord.tranche_id == tranche.id)
            .order_by(RepaymentRecord.emi_num)
            .all()
        )

        for record in records:
            if record.payment_status in {"pending", "late"}:
                # Approximate principal and interest split (50-50 for simplicity)
                principal = record.amount * 0.5
                interest = record.amount * 0.5

                return NextEMIOut(
                    tranche_num=tranche.tranche_num,
                    emi_num=record.emi_num,
                    due_date=record.due_date.isoformat(),
                    amount=record.amount,
                    principal=principal,
                    interest=interest,
                )

    return None


@router.get("/audit/repayment-monitor", response_model=list[RepaymentMonitorOut])
def repayment_monitor(
    db: Session = Depends(get_db),
) -> list[RepaymentMonitorOut]:
    """
    Officer view of all borrowers' EMI status and repayment performance.
    """
    # Get all applications
    applications = db.query(Application).all()

    monitor_data = []
    for app in applications:
        # Get latest decision
        decision = (
            db.query(Decision)
            .filter(Decision.application_id == app.id)
            .order_by(Decision.created_at.desc())
            .first()
        )

        if not decision:
            continue

        tier = decision.tier
        approved_amount = 0.0

        # Get borrower email
        borrower = db.query(User).filter(User.id == app.borrower_id).first()
        borrower_email = borrower.email if borrower else "unknown"

        # Count EMI statuses
        tranches = (
            db.query(Tranche)
            .filter(Tranche.application_id == app.id)
            .all()
        )

        on_time = 0
        late = 0
        missed = 0
        bounced = 0
        last_emi_date = None

        for tranche in tranches:
            approved_amount += tranche.amount
            records = (
                db.query(RepaymentRecord)
                .filter(RepaymentRecord.tranche_id == tranche.id)
                .all()
            )

            for record in records:
                if record.payment_status == "ontime":
                    on_time += 1
                elif record.payment_status == "late":
                    late += 1
                elif record.payment_status == "missed":
                    missed += 1
                elif record.payment_status == "bounced":
                    bounced += 1

                if record.paid_date and (
                    last_emi_date is None or record.paid_date > last_emi_date
                ):
                    last_emi_date = record.paid_date

        # Check if stop rule is active
        from app.models import StopRule

        stop_rule = (
            db.query(StopRule)
            .filter(
                StopRule.application_id == app.id,
                StopRule.unfrozen_date == None,
            )
            .first()
        )
        stop_active = stop_rule is not None

        monitor_data.append(
            RepaymentMonitorOut(
                application_id=app.id,
                borrower_email=borrower_email,
                tier=tier if tier else 0,
                total_approved_amount=approved_amount,
                on_time_count=on_time,
                late_count=late,
                missed_count=missed,
                bounced_count=bounced,
                stop_rule_active=stop_active,
                last_emi_date=last_emi_date.isoformat() if last_emi_date else None,
            )
        )

    return monitor_data
