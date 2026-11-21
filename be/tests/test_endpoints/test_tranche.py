"""Tests for tranche endpoints: eligibility check and approval."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import (
    User,
    Application,
    Shop,
    Tranche,
    RepaymentRecord,
    AuditLog,
)
from app.utils import utcnow_naive


@pytest.fixture
def officer_user(db_session: Session) -> User:
    """Create an officer user for approvals."""
    user = User(
        email="officer@test.com",
        password_hash="hashed_password",
        role="officer",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def borrower_user(db_session: Session) -> User:
    """Create a borrower user."""
    user = User(
        email="borrower@test.com",
        password_hash="hashed_password",
        role="borrower",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def shop(db_session: Session) -> Shop:
    """Create a test shop."""
    shop = Shop(
        shop_id=1,
        gstin="36AABCT1234H1Z0",
        shop_name="Test Shop",
        shop_category="retail",
        state_code="TG",
        gstin_valid=True,
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)
    return shop


@pytest.fixture
def application(db_session: Session, borrower_user: User, shop: Shop) -> Application:
    """Create a test application."""
    app = Application(
        borrower_id=borrower_user.id,
        shop_id=shop.id,
        loan_amount_requested=50000,
        status="approved",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    return app


@pytest.fixture
def tranche_with_ontime_emis(
    db_session: Session, application: Application
) -> tuple[Tranche, list[RepaymentRecord]]:
    """Create tranche 1 with all on-time EMIs."""
    tranche = Tranche(
        application_id=application.id,
        tranche_num=1,
        amount=25000,
        release_date=utcnow_naive(),
        release_status="released",
        emi_count=12,
        tenor_months=12,
    )
    db_session.add(tranche)
    db_session.flush()

    # Create 12 on-time EMI records
    emis = []
    due_date = utcnow_naive() + timedelta(days=30)
    for i in range(1, 13):
        emi = RepaymentRecord(
            tranche_id=tranche.id,
            emi_num=i,
            due_date=due_date,
            amount=2100,
            paid_date=due_date - timedelta(days=2),  # 2 days early
            payment_status="ontime",
            days_late=0,
        )
        emis.append(emi)
        db_session.add(emi)
        due_date += timedelta(days=30)

    db_session.commit()
    return tranche, emis


@pytest.fixture
def tranche_with_late_emi(
    db_session: Session, application: Application
) -> tuple[Tranche, list[RepaymentRecord]]:
    """Create tranche 1 with one late EMI."""
    tranche = Tranche(
        application_id=application.id,
        tranche_num=1,
        amount=25000,
        release_date=utcnow_naive(),
        release_status="released",
        emi_count=12,
        tenor_months=12,
    )
    db_session.add(tranche)
    db_session.flush()

    # Create EMI records with one late payment
    emis = []
    due_date = utcnow_naive() + timedelta(days=30)
    for i in range(1, 13):
        if i == 3:
            # Third EMI is paid late
            emi = RepaymentRecord(
                tranche_id=tranche.id,
                emi_num=i,
                due_date=due_date,
                amount=2100,
                paid_date=due_date + timedelta(days=5),  # 5 days late
                payment_status="late",
                days_late=5,
            )
        else:
            # Others are on-time
            emi = RepaymentRecord(
                tranche_id=tranche.id,
                emi_num=i,
                due_date=due_date,
                amount=2100,
                paid_date=due_date - timedelta(days=2),
                payment_status="ontime",
                days_late=0,
            )
        emis.append(emi)
        db_session.add(emi)
        due_date += timedelta(days=30)

    db_session.commit()
    return tranche, emis


@pytest.fixture
def tranche_with_missing_emi(
    db_session: Session, application: Application
) -> tuple[Tranche, list[RepaymentRecord]]:
    """Create tranche 1 with a missing (unpaid) EMI."""
    tranche = Tranche(
        application_id=application.id,
        tranche_num=1,
        amount=25000,
        release_date=utcnow_naive(),
        release_status="released",
        emi_count=12,
        tenor_months=12,
    )
    db_session.add(tranche)
    db_session.flush()

    # Create EMI records with one missed/pending
    emis = []
    due_date = utcnow_naive() + timedelta(days=30)
    for i in range(1, 13):
        if i == 5:
            # Fifth EMI is missed
            emi = RepaymentRecord(
                tranche_id=tranche.id,
                emi_num=i,
                due_date=due_date,
                amount=2100,
                paid_date=None,
                payment_status="missed",
                days_late=0,
            )
        else:
            # Others are on-time
            emi = RepaymentRecord(
                tranche_id=tranche.id,
                emi_num=i,
                due_date=due_date,
                amount=2100,
                paid_date=due_date - timedelta(days=2),
                payment_status="ontime",
                days_late=0,
            )
        emis.append(emi)
        db_session.add(emi)
        due_date += timedelta(days=30)

    db_session.commit()
    return tranche, emis


@pytest.fixture
def tranche_2_pending(
    db_session: Session, application: Application, tranche_with_ontime_emis
) -> Tranche:
    """Create tranche 2 (pending, depends on tranche 1)."""
    tranche = Tranche(
        application_id=application.id,
        tranche_num=2,
        amount=25000,
        release_date=utcnow_naive() + timedelta(days=400),
        release_status="pending",
        emi_count=12,
        tenor_months=12,
    )
    db_session.add(tranche)
    db_session.commit()
    db_session.refresh(tranche)
    return tranche


class TestTrancheEligibilityEndpoint:
    """Test GET /api/applications/{id}/tranches/{tranche_num}/eligibility"""

    def test_eligible_scenario_all_emis_ontime(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending
    ):
        """Test: all EMIs on-time → tranche 2 eligible."""
        response = client.get(
            f"/api/applications/{application.id}/tranches/2/eligibility"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is True
        assert "All previous tranches' EMIs are on-time" in data["reason"]
        assert data["release_date"] is not None

    def test_not_eligible_one_late_emi(
        self, client, application, tranche_with_late_emi, db_session
    ):
        """Test: one late EMI in tranche 1 → tranche 2 not eligible."""
        # Create tranche 2 pending
        tranche_2 = Tranche(
            application_id=application.id,
            tranche_num=2,
            amount=25000,
            release_date=utcnow_naive() + timedelta(days=400),
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche_2)
        db_session.commit()

        response = client.get(
            f"/api/applications/{application.id}/tranches/2/eligibility"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is False
        assert "late" in data["reason"].lower()

    def test_not_eligible_missing_emi(
        self, client, application, tranche_with_missing_emi, db_session
    ):
        """Test: missing EMI in tranche 1 → tranche 2 not eligible."""
        # Create tranche 2 pending
        tranche_2 = Tranche(
            application_id=application.id,
            tranche_num=2,
            amount=25000,
            release_date=utcnow_naive() + timedelta(days=400),
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche_2)
        db_session.commit()

        response = client.get(
            f"/api/applications/{application.id}/tranches/2/eligibility"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is False
        assert "missed" in data["reason"].lower()

    def test_eligibility_first_tranche(self, client, application, db_session):
        """Test: first tranche is always eligible if pending."""
        tranche = Tranche(
            application_id=application.id,
            tranche_num=1,
            amount=25000,
            release_date=utcnow_naive(),
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche)
        db_session.commit()

        response = client.get(
            f"/api/applications/{application.id}/tranches/1/eligibility"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["eligible"] is True
        assert "First tranche" in data["reason"]

    def test_eligibility_tranche_not_found(self, client, application):
        """Test: non-existent tranche returns 404."""
        response = client.get(
            f"/api/applications/{application.id}/tranches/999/eligibility"
        )
        assert response.status_code == 404
        assert "Tranche not found" in response.json()["detail"]

    def test_eligibility_application_not_found(self, client):
        """Test: non-existent application returns 404."""
        response = client.get("/api/applications/999/tranches/1/eligibility")
        assert response.status_code == 404
        assert "Application not found" in response.json()["detail"]

    def test_eligibility_creates_audit_log(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending, db_session
    ):
        """Test: eligibility check creates an audit log entry."""
        # Clear any existing audit logs
        db_session.query(AuditLog).delete()
        db_session.commit()

        response = client.get(
            f"/api/applications/{application.id}/tranches/2/eligibility"
        )
        assert response.status_code == 200

        # Check that audit log was created
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "tranche",
            AuditLog.action == "eligibility_checked",
        ).all()
        assert len(audit_logs) == 1
        assert "tranche_num" in audit_logs[0].details_json


class TestTrancheApprovalEndpoint:
    """Test POST /api/applications/{id}/tranches/{tranche_num}/approve"""

    def test_approve_eligible_tranche(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending, 
        officer_user, db_session
    ):
        """Test: approve eligible tranche → release_status changes to 'released'."""
        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/2/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "tranche_details" in data
        assert "release_date" in data
        assert "audit_entry_id" in data
        
        # Verify tranche details
        tranche_details = data["tranche_details"]
        assert tranche_details["release_status"] == "released"
        assert tranche_details["tranche_num"] == 2
        assert tranche_details["amount"] == 25000
        assert "repayment_history" in tranche_details

        # Verify tranche was actually updated in DB
        tranche = db_session.query(Tranche).filter(
            Tranche.application_id == application.id,
            Tranche.tranche_num == 2,
        ).first()
        assert tranche.release_status == "released"
        assert tranche.release_date is not None

    def test_approve_ineligible_tranche_returns_error(
        self, client, application, tranche_with_late_emi, db_session, officer_user
    ):
        """Test: approve ineligible tranche → returns 400 with reason."""
        # Create tranche 2 pending
        tranche_2 = Tranche(
            application_id=application.id,
            tranche_num=2,
            amount=25000,
            release_date=utcnow_naive() + timedelta(days=400),
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche_2)
        db_session.commit()

        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/2/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "late" in response.json()["detail"].lower()

    def test_approve_creates_audit_log(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending, 
        officer_user, db_session
    ):
        """Test: approval creates audit log with officer info."""
        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/2/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "tranche",
            AuditLog.action == "approved",
        ).first()
        assert audit_log is not None
        assert audit_log.officer_id == officer_user.id
        assert officer_user.email in audit_log.details_json

    def test_approve_already_released_tranche(
        self, client, application, db_session, officer_user
    ):
        """Test: approving already-released tranche → returns 400."""
        # Create already-released tranche
        tranche = Tranche(
            application_id=application.id,
            tranche_num=1,
            amount=25000,
            release_date=utcnow_naive(),
            release_status="released",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche)
        db_session.commit()

        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/1/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "already released" in response.json()["detail"].lower()

    def test_approve_repaid_tranche(
        self, client, application, db_session, officer_user
    ):
        """Test: approving repaid tranche → returns 400."""
        # Create already-repaid tranche
        tranche = Tranche(
            application_id=application.id,
            tranche_num=1,
            amount=25000,
            release_date=utcnow_naive(),
            release_status="repaid",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche)
        db_session.commit()

        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/1/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "repaid" in response.json()["detail"].lower()

    def test_approve_without_auth_returns_401(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending
    ):
        """Test: unauthenticated approval request → returns 401."""
        response = client.post(
            f"/api/applications/{application.id}/tranches/2/approve",
        )
        assert response.status_code == 401

    def test_approve_sets_release_date(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending, 
        officer_user, db_session
    ):
        """Test: approval sets release_date to today."""
        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)
        before_approval = utcnow_naive()

        response = client.post(
            f"/api/applications/{application.id}/tranches/2/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        after_approval = utcnow_naive()

        # Verify release_date is set in response
        data = response.json()
        release_date_str = data["release_date"]
        release_date = datetime.fromisoformat(release_date_str)

        # Verify it's approximately now (within a few seconds)
        assert before_approval <= release_date <= after_approval

    def test_approve_nonexistent_tranche(
        self, client, application, officer_user
    ):
        """Test: approve non-existent tranche → returns 404."""
        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/999/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "Tranche not found" in response.json()["detail"]

    def test_approve_nonexistent_application(
        self, client, officer_user
    ):
        """Test: approve tranche in non-existent application → returns 404."""
        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/999/tranches/1/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "Application not found" in response.json()["detail"]

    def test_approve_includes_repayment_history(
        self, client, application, tranche_with_ontime_emis, tranche_2_pending,
        officer_user, db_session
    ):
        """Test: approval response includes all EMIs in repayment_history."""
        # Create tranche 2 with some repayment records
        tranche_2 = db_session.query(Tranche).filter(
            Tranche.application_id == application.id,
            Tranche.tranche_num == 2,
        ).first()

        # Add some EMIs to tranche 2
        due_date = utcnow_naive() + timedelta(days=30)
        for i in range(1, 4):  # Add 3 EMIs
            emi = RepaymentRecord(
                tranche_id=tranche_2.id,
                emi_num=i,
                due_date=due_date,
                amount=2100,
                paid_date=None,
                payment_status="pending",
                days_late=0,
            )
            db_session.add(emi)
            due_date += timedelta(days=30)
        db_session.commit()

        # Login as officer
        from app.auth import create_access_token
        token = create_access_token(officer_user.id)

        response = client.post(
            f"/api/applications/{application.id}/tranches/2/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        data = response.json()
        repayment_history = data["tranche_details"]["repayment_history"]
        assert len(repayment_history) == 3
        assert all("emi_num" in emi for emi in repayment_history)
        assert all("due_date" in emi for emi in repayment_history)
        assert all("payment_status" in emi for emi in repayment_history)
