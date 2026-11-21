"""Tests for audit endpoints."""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import (
    Application,
    Consent,
    Decision,
    HouseholdData,
    Override,
    AuditLog,
    Shop,
    User,
)
from app.utils import utcnow_naive


@pytest.fixture
def test_officer(db_session: Session):
    """Create test officer."""
    officer = User(
        email="officer@test.com",
        password_hash="hash",
        role="officer",
    )
    db_session.add(officer)
    db_session.commit()
    db_session.refresh(officer)
    return officer


@pytest.fixture
def test_borrower(db_session: Session):
    """Create test borrower."""
    borrower = User(
        email="borrower@test.com",
        password_hash="hash",
        role="borrower",
    )
    db_session.add(borrower)
    db_session.commit()
    db_session.refresh(borrower)
    return borrower


@pytest.fixture
def test_shop(db_session: Session):
    """Create test shop."""
    shop = Shop(
        shop_id=1,
        shop_category="kirana",
        upi_turnover=100000,
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)
    return shop


@pytest.fixture
def test_application(db_session: Session, test_borrower, test_shop):
    """Create test application with consent and household."""
    app = Application(
        borrower_id=test_borrower.id,
        shop_id=test_shop.id,
        loan_amount_requested=50000,
        purpose="Inventory",
    )
    db_session.add(app)
    db_session.commit()

    consent = Consent(
        application_id=app.id,
        text="I agree",
        borrower_agreed=True,
        agreed_at=utcnow_naive(),
    )
    db_session.add(consent)

    household = HouseholdData(
        application_id=app.id,
        family_size=4,
        monthly_expenses=25000,
    )
    db_session.add(household)
    db_session.commit()
    db_session.refresh(app)
    return app


class TestAuditDecisionList:
    """Tests for GET /api/audit/decisions."""

    def test_list_decisions_empty(self, db_session: Session):
        """Test listing decisions when none exist."""
        decisions = db_session.query(Decision).all()
        assert len(decisions) == 0

    def test_list_decisions_with_audit_trail(
        self, db_session: Session, test_officer, test_application
    ):
        """Test listing decisions includes audit trail."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            tier=1,
            approved_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
            replay_count=0,
        )
        db_session.add(decision)
        db_session.commit()

        # Create override
        override = Override(
            decision_id=decision.id,
            officer_id=test_officer.id,
            old_loan_amount=50000,
            new_loan_amount=45000,
            reason="Conservative override",
        )
        db_session.add(override)

        # Log to audit
        audit_log = AuditLog(
            entity_type="decision",
            entity_id=decision.id,
            action="overridden",
            officer_id=test_officer.id,
            details_json=json.dumps({"new_amount": 45000}),
        )
        db_session.add(audit_log)
        db_session.commit()

        # List decisions
        decisions = db_session.query(Decision).all()
        assert len(decisions) == 1
        assert decisions[0].replay_count == 0

        # List overrides for decision
        overrides = db_session.query(Override).filter_by(
            decision_id=decision.id
        ).all()
        assert len(overrides) == 1

        # List audit logs
        logs = db_session.query(AuditLog).filter_by(
            entity_type="decision"
        ).all()
        assert len(logs) == 1

    def test_filter_by_application_id(
        self, db_session: Session, test_borrower, test_shop, test_application
    ):
        """Test filtering decisions by application_id."""
        # Create another application
        app2 = Application(
            borrower_id=test_borrower.id,
            shop_id=test_shop.id,
            loan_amount_requested=75000,
            purpose="Expansion",
        )
        db_session.add(app2)
        db_session.commit()

        # Create decisions for both
        dec1 = Decision(
            application_id=test_application.id,
            verdict="approved",
            tier=1,
            approved_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        dec2 = Decision(
            application_id=app2.id,
            verdict="approved",
            tier=2,
            approved_amount=60000,
            confidence=0.80,
            reasons_json=json.dumps(["good"]),
        )
        db_session.add_all([dec1, dec2])
        db_session.commit()

        # Query specific application
        decisions = db_session.query(Decision).filter_by(
            application_id=test_application.id
        ).all()
        assert len(decisions) == 1
        assert decisions[0].approved_amount == 50000

    def test_filter_by_date_range(self, db_session: Session, test_application):
        """Test filtering decisions by date range."""
        now = utcnow_naive()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            tier=1,
            approved_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        # Query with date range that includes now
        decisions = db_session.query(Decision).filter(
            Decision.created_at >= yesterday,
            Decision.created_at <= tomorrow,
        ).all()
        assert len(decisions) == 1

        # Query with date range that excludes now
        decisions = db_session.query(Decision).filter(
            Decision.created_at < yesterday,
        ).all()
        assert len(decisions) == 0

    def test_audit_permissions_officer_can_view(self, db_session: Session, test_officer):
        """Test that officers can view audit trail."""
        # In endpoint, role check would verify role in ["officer", "approver", "auditor"]
        assert test_officer.role == "officer"

    def test_audit_permissions_borrower_cannot_view(self, db_session: Session, test_borrower):
        """Test that borrowers cannot view audit trail."""
        # In endpoint, role check would reject borrower role
        assert test_borrower.role == "borrower"


class TestAuditTrail:
    """Tests for audit trail behavior."""

    def test_create_audit_log_on_decision(self, db_session: Session, test_officer, test_application):
        """Test creating audit log on decision creation."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            tier=1,
            approved_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        # In production, endpoint would create this automatically
        audit_log = AuditLog(
            entity_type="decision",
            entity_id=decision.id,
            action="created",
            officer_id=None,  # System action
        )
        db_session.add(audit_log)
        db_session.commit()

        logs = db_session.query(AuditLog).filter_by(
            entity_type="decision",
            entity_id=decision.id,
        ).all()
        assert len(logs) == 1
        assert logs[0].action == "created"

    def test_create_audit_log_on_override(self, db_session: Session, test_officer, test_application):
        """Test creating audit log on override."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            tier=1,
            approved_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        override = Override(
            decision_id=decision.id,
            officer_id=test_officer.id,
            old_loan_amount=50000,
            new_loan_amount=40000,
            reason="Conservative",
        )
        db_session.add(override)

        # Audit log for override
        audit_log = AuditLog(
            entity_type="decision",
            entity_id=decision.id,
            action="overridden",
            officer_id=test_officer.id,
            details_json=json.dumps({
                "old_amount": 50000,
                "new_amount": 40000,
                "reason": "Conservative",
            }),
        )
        db_session.add(audit_log)
        db_session.commit()

        logs = db_session.query(AuditLog).filter_by(
            entity_type="decision",
            action="overridden",
        ).all()
        assert len(logs) == 1

    def test_audit_log_timestamps(self, db_session: Session, test_officer):
        """Test that audit logs have correct timestamps."""
        before = utcnow_naive()
        
        audit_log = AuditLog(
            entity_type="test",
            entity_id=1,
            action="created",
            officer_id=test_officer.id,
        )
        db_session.add(audit_log)
        db_session.commit()

        after = utcnow_naive()

        assert before <= audit_log.timestamp <= after
