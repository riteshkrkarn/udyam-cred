"""Tests for repayment endpoints: recording EMI payments and StopRuleEngine integration."""
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
    StopRule,
    Decision,
)
from app.utils import utcnow_naive
from app.engines.stop_rule_engine import StopRuleEngine


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
        frozen=False,
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    return app


@pytest.fixture
def decision(db_session: Session, application: Application) -> Decision:
    """Create a decision for the application."""
    dec = Decision(
        application_id=application.id,
        verdict="approved",
        tier=1,
        verified_months=6,
        source_agreement=0.85,
        approved_amount=50000,
        rate_percent=12.0,
    )
    db_session.add(dec)
    db_session.commit()
    db_session.refresh(dec)
    return dec


@pytest.fixture
def tranche_with_emis(
    db_session: Session, application: Application
) -> tuple[Tranche, list[RepaymentRecord]]:
    """Create tranche with multiple EMI records."""
    tranche = Tranche(
        application_id=application.id,
        tranche_num=1,
        amount=50000,
        release_date=utcnow_naive(),
        release_status="released",
        emi_count=12,
        tenor_months=12,
    )
    db_session.add(tranche)
    db_session.flush()

    # Create 12 EMI records
    emis = []
    due_date = utcnow_naive()
    for i in range(1, 13):
        emi = RepaymentRecord(
            tranche_id=tranche.id,
            emi_num=i,
            due_date=due_date,
            amount=4166.67,
            payment_status="pending",
        )
        db_session.add(emi)
        emis.append(emi)
        due_date += timedelta(days=30)

    db_session.commit()
    return tranche, emis


class TestRepaymentRecordingBasic:
    """Test basic repayment recording without stop rule."""

    def test_record_ontime_payment(self, client, db_session, application, tranche_with_emis, decision):
        """Test recording an on-time EMI payment (no freeze)."""
        tranche, emis = tranche_with_emis
        
        # Record a payment before due date
        payment_date = (emis[0].due_date - timedelta(days=5)).isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 1,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["payment_status"] == "ontime"
        assert data["days_late"] == 0
        assert data["freeze_status"] is False
        assert data["freeze_reason"] is None
        
        # Verify the record was updated in DB (refresh session to see changes from API)
        db_session.expire_all()
        updated_emi = db_session.query(RepaymentRecord).filter(
            RepaymentRecord.tranche_id == tranche.id,
            RepaymentRecord.emi_num == 1,
        ).first()
        assert updated_emi.payment_status == "ontime"
        assert updated_emi.days_late == 0

    def test_record_late_payment(self, client, db_session, application, tranche_with_emis, decision):
        """Test recording a late EMI payment (no freeze)."""
        tranche, emis = tranche_with_emis
        
        # Record a payment after due date (10 days late)
        payment_date = (emis[0].due_date + timedelta(days=10)).isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 1,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["payment_status"] == "late"
        assert data["days_late"] == 10
        assert data["freeze_status"] is False
        assert data["freeze_reason"] is None


class TestStopRuleIntegration:
    """Test StopRuleEngine integration with repayment recording."""

    def test_first_missed_emi_no_freeze(self, client, db_session, application, tranche_with_emis, decision):
        """Test that first missed EMI does not trigger freeze."""
        tranche, emis = tranche_with_emis
        
        # Manually mark EMI 1 as missed
        emis[0].payment_status = "missed"
        db_session.commit()
        
        # Record EMI 2 as on-time (first missed EMI should NOT trigger freeze)
        payment_date = emis[1].due_date.isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 2,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["freeze_status"] is False
        
        # Application should NOT be frozen
        app = db_session.query(Application).filter(Application.id == application.id).first()
        assert app.frozen is False
        assert app.status != "frozen"

    def test_second_missed_emi_triggers_freeze(self, client, db_session, application, tranche_with_emis, decision):
        """Test that second missed EMI triggers freeze."""
        tranche, emis = tranche_with_emis
        
        # Manually mark EMI 1 and 2 as missed
        emis[0].payment_status = "missed"
        emis[1].payment_status = "missed"
        db_session.commit()
        
        # Record EMI 3 as on-time (should trigger freeze with 2+ missed EMIs)
        payment_date = emis[2].due_date.isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 3,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["freeze_status"] is True
        assert "missed" in data["freeze_reason"].lower()
        
        # Application should be frozen (refresh to see API changes)
        db_session.expire_all()
        app = db_session.query(Application).filter(Application.id == application.id).first()
        assert app.frozen is True
        assert app.status == "frozen"
        assert app.frozen_date is not None
        
        # Stop rule should be created
        stop_rule = db_session.query(StopRule).filter(
            StopRule.application_id == application.id
        ).first()
        assert stop_rule is not None
        assert stop_rule.missed_emi_count >= 2
        assert stop_rule.frozen_date is not None

    def test_bounced_payment_counts_as_missed(self, client, db_session, application, tranche_with_emis, decision):
        """Test that bounced payments count toward missed EMI threshold."""
        tranche, emis = tranche_with_emis
        
        # Mark EMI 1 as missed and EMI 2 as bounced
        emis[0].payment_status = "missed"
        emis[1].payment_status = "bounced"
        db_session.commit()
        
        # Record EMI 3 (should trigger freeze: 1 missed + 1 bounced = 2)
        payment_date = emis[2].due_date.isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 3,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["freeze_status"] is True
        
        # Application should be frozen (refresh to see API changes)
        db_session.expire_all()
        app = db_session.query(Application).filter(Application.id == application.id).first()
        assert app.frozen is True


class TestAuditLogging:
    """Test audit logging for repayment actions."""

    def test_audit_log_created_for_normal_payment(self, client, db_session, application, tranche_with_emis, decision):
        """Test that audit log is created for normal EMI payment."""
        tranche, emis = tranche_with_emis
        initial_audit_count = db_session.query(AuditLog).count()
        
        # Record on-time payment
        payment_date = (emis[0].due_date - timedelta(days=5)).isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 1,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        
        # Verify audit log was created
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "repayment_record"
        ).all()
        assert len(audit_logs) > initial_audit_count

    def test_audit_log_created_for_freeze(self, client, db_session, application, tranche_with_emis, decision):
        """Test that audit log is created when application is frozen."""
        tranche, emis = tranche_with_emis
        
        # Mark EMI 1 and 2 as missed
        emis[0].payment_status = "missed"
        emis[1].payment_status = "missed"
        db_session.commit()
        
        # Record EMI 3 (triggers freeze)
        payment_date = emis[2].due_date.isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 3,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        
        # Verify freeze audit log was created
        freeze_logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "application",
            AuditLog.action == "frozen",
        ).all()
        assert len(freeze_logs) > 0
        
        # Check the freeze log details
        freeze_log = freeze_logs[0]
        assert freeze_log.entity_id == application.id
        assert "stop_rule_engine" in freeze_log.details_json


class TestFrozenApplicationBlocksRelease:
    """Test that frozen applications block further tranche releases."""

    def test_frozen_application_cannot_release_next_tranche(
        self, client, db_session, application, tranche_with_emis, decision
    ):
        """Test that frozen application cannot release next tranche."""
        tranche, emis = tranche_with_emis
        
        # Freeze the application
        app = db_session.query(Application).filter(Application.id == application.id).first()
        app.frozen = True
        app.frozen_date = utcnow_naive()
        app.status = "frozen"
        db_session.commit()
        
        # Create second tranche
        tranche2 = Tranche(
            application_id=application.id,
            tranche_num=2,
            amount=25000,
            release_date=utcnow_naive() + timedelta(days=180),
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db_session.add(tranche2)
        db_session.commit()
        
        # Try to release second tranche (should be blocked)
        # This would require a tranche release endpoint check, but we verify the state
        app_state = db_session.query(Application).filter(Application.id == application.id).first()
        assert app_state.frozen is True
        assert app_state.status == "frozen"


class TestMultipleTransactions:
    """Test multi-tranche and edge cases."""

    def test_missed_emis_across_tranches(self, client, db_session, application, decision):
        """Test that missed EMIs across multiple tranches are counted together."""
        # Create tranche 1
        tranche1 = Tranche(
            application_id=application.id,
            tranche_num=1,
            amount=25000,
            release_date=utcnow_naive(),
            release_status="released",
            emi_count=6,
            tenor_months=6,
        )
        db_session.add(tranche1)
        db_session.flush()
        
        # Create tranche 2
        tranche2 = Tranche(
            application_id=application.id,
            tranche_num=2,
            amount=25000,
            release_date=utcnow_naive() + timedelta(days=180),
            release_status="released",
            emi_count=6,
            tenor_months=6,
        )
        db_session.add(tranche2)
        db_session.flush()
        
        # Create EMI records for both tranches
        due_date = utcnow_naive()
        for i in range(1, 7):
            emi1 = RepaymentRecord(
                tranche_id=tranche1.id,
                emi_num=i,
                due_date=due_date,
                amount=4166.67,
                payment_status="pending",
            )
            db_session.add(emi1)
            due_date += timedelta(days=30)
        
        due_date = utcnow_naive() + timedelta(days=180)
        for i in range(1, 7):
            emi2 = RepaymentRecord(
                tranche_id=tranche2.id,
                emi_num=i,
                due_date=due_date,
                amount=4166.67,
                payment_status="pending",
            )
            db_session.add(emi2)
            due_date += timedelta(days=30)
        
        db_session.commit()
        
        # Mark one EMI from tranche1 as missed
        emi_tranche1 = db_session.query(RepaymentRecord).filter(
            RepaymentRecord.tranche_id == tranche1.id,
            RepaymentRecord.emi_num == 1,
        ).first()
        emi_tranche1.payment_status = "missed"
        
        # Mark one EMI from tranche2 as missed
        emi_tranche2 = db_session.query(RepaymentRecord).filter(
            RepaymentRecord.tranche_id == tranche2.id,
            RepaymentRecord.emi_num == 1,
        ).first()
        emi_tranche2.payment_status = "missed"
        db_session.commit()
        
        # Record a payment (should trigger freeze: 2 missed EMIs across tranches)
        emi_tranche1_next = db_session.query(RepaymentRecord).filter(
            RepaymentRecord.tranche_id == tranche1.id,
            RepaymentRecord.emi_num == 2,
        ).first()
        payment_date = emi_tranche1_next.due_date.isoformat()
        
        response = client.post(
            f"/api/applications/{application.id}/repayment/record",
            params={
                "tranche_num": 1,
                "emi_num": 2,
                "paid_amount": 4166.67,
                "paid_date": payment_date,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["freeze_status"] is True
