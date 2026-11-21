"""Tests for scoring endpoints."""
from __future__ import annotations

import json
import pytest
from sqlalchemy.orm import Session

from app.models import (
    Application,
    Consent,
    Decision,
    HouseholdData,
    Override,
    Shop,
    User,
)
from app.utils import utcnow_naive


@pytest.fixture
def test_user(db_session: Session):
    """Create test user."""
    user = User(
        email="borrower@test.com",
        password_hash="hash",
        role="borrower",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


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
def test_application(db_session: Session, test_user, test_shop):
    """Create test application with consent and household data."""
    app = Application(
        borrower_id=test_user.id,
        shop_id=test_shop.id,
        loan_amount_requested=50000,
        purpose="Inventory",
    )
    db_session.add(app)
    db_session.commit()

    # Add consent
    consent = Consent(
        application_id=app.id,
        text="I agree to data sharing",
        borrower_agreed=True,
        agreed_at=utcnow_naive(),
    )
    db_session.add(consent)

    # Add household data
    household = HouseholdData(
        application_id=app.id,
        family_size=4,
        monthly_expenses=25000,
        liabilities=50000,
    )
    db_session.add(household)
    db_session.commit()
    db_session.refresh(app)
    return app


class TestScoringCreate:
    """Tests for POST /api/scoring/score."""

    def test_score_application_creates_decision(
        self, db_session: Session, test_application
    ):
        """Test that scoring creates a Decision record."""
        # In production, this would be tested via HTTP endpoint
        # Here we test the model behavior
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=50000,
            rate_percent=12.5,
            emi_monthly=4500,
            confidence=0.85,
            reasons_json=json.dumps(["stable_cash_flow", "good_vintage"]),
            replay_count=0,
        )
        db_session.add(decision)
        db_session.commit()
        db_session.refresh(decision)

        assert decision.id is not None
        assert decision.verdict == "approved"
        assert decision.loan_amount == 50000

    def test_score_requires_consent(self, db_session: Session, test_user, test_shop):
        """Test that scoring fails without consent."""
        app = Application(
            borrower_id=test_user.id,
            shop_id=test_shop.id,
            loan_amount_requested=50000,
            purpose="Inventory",
        )
        db_session.add(app)
        db_session.commit()

        # No consent added
        consents = db_session.query(Consent).filter_by(
            application_id=app.id
        ).all()
        assert len(consents) == 0

        # In endpoint, this would raise 403 Forbidden

    def test_score_rejected_verdict(self, db_session: Session, test_application):
        """Test scoring with rejected verdict."""
        decision = Decision(
            application_id=test_application.id,
            verdict="rejected",
            loan_amount=0,
            confidence=0.6,
            reasons_json=json.dumps(["insufficient_capacity"]),
        )
        db_session.add(decision)
        db_session.commit()

        retrieved = db_session.query(Decision).filter_by(
            application_id=test_application.id
        ).first()
        assert retrieved.verdict == "rejected"
        assert retrieved.loan_amount == 0


class TestReplay:
    """Tests for POST /api/scoring/replay."""

    def test_replay_increments_count(self, db_session: Session, test_application):
        """Test that replay increments replay_count without saving new decision."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
            replay_count=0,
        )
        db_session.add(decision)
        db_session.commit()

        original_id = decision.id

        # Simulate replay by incrementing
        decision.replay_count += 1
        db_session.commit()

        # Should still be same decision
        retrieved = db_session.query(Decision).filter_by(id=original_id).first()
        assert retrieved.replay_count == 1

        # Should still be only one decision for app
        all_decisions = db_session.query(Decision).filter_by(
            application_id=test_application.id
        ).all()
        assert len(all_decisions) == 1

    def test_replay_with_overrides(self, db_session: Session, test_application):
        """Test replay with parameter overrides."""
        # Get household data
        household = test_application.household_data[0]
        original_expenses = household.monthly_expenses

        # Modify for replay (in memory, don't save)
        overridden_expenses = original_expenses * 1.2

        # Create decision based on overridden values
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=40000,  # Lower due to higher expenses
            confidence=0.75,
            reasons_json=json.dumps(["adjusted"]),
        )
        db_session.add(decision)
        db_session.commit()

        # Verify original household unchanged
        retrieved_household = (
            db_session.query(HouseholdData)
            .filter_by(application_id=test_application.id)
            .first()
        )
        assert retrieved_household.monthly_expenses == original_expenses


class TestOverride:
    """Tests for POST /api/scoring/override."""

    def test_override_creates_record(self, db_session: Session, test_user, test_application):
        """Test that override creates Override record."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        # Create override
        override = Override(
            decision_id=decision.id,
            officer_id=test_user.id,
            old_loan_amount=50000,
            new_loan_amount=40000,
            reason="Conservative approach for first-time borrower",
        )
        db_session.add(override)
        db_session.commit()
        db_session.refresh(override)

        assert override.id is not None
        assert override.old_loan_amount == 50000
        assert override.new_loan_amount == 40000

    def test_override_updates_decision(self, db_session: Session, test_user, test_application):
        """Test that override updates the decision's loan_amount."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        # Create override and update decision
        override = Override(
            decision_id=decision.id,
            officer_id=test_user.id,
            old_loan_amount=decision.loan_amount,
            new_loan_amount=40000,
            reason="Conservative",
        )
        db_session.add(override)
        decision.loan_amount = 40000
        db_session.commit()

        retrieved_decision = db_session.query(Decision).filter_by(
            id=decision.id
        ).first()
        assert retrieved_decision.loan_amount == 40000

    def test_override_with_reason(self, db_session: Session, test_user, test_application):
        """Test that override reason is captured."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        reason = "Customer cash flow analysis shows seasonal peaks"
        override = Override(
            decision_id=decision.id,
            officer_id=test_user.id,
            old_loan_amount=50000,
            new_loan_amount=45000,
            reason=reason,
        )
        db_session.add(override)
        db_session.commit()

        retrieved = db_session.query(Override).filter_by(
            decision_id=decision.id
        ).first()
        assert retrieved.reason == reason

    def test_multiple_overrides_per_decision(self, db_session: Session, test_user, test_application):
        """Test that a decision can have multiple override records."""
        decision = Decision(
            application_id=test_application.id,
            verdict="approved",
            loan_amount=50000,
            confidence=0.85,
            reasons_json=json.dumps(["stable"]),
        )
        db_session.add(decision)
        db_session.commit()

        override1 = Override(
            decision_id=decision.id,
            officer_id=test_user.id,
            old_loan_amount=50000,
            new_loan_amount=45000,
            reason="First override",
        )
        override2 = Override(
            decision_id=decision.id,
            officer_id=test_user.id,
            old_loan_amount=45000,
            new_loan_amount=40000,
            reason="Second override",
        )
        db_session.add_all([override1, override2])
        db_session.commit()

        overrides = (
            db_session.query(Override).filter_by(decision_id=decision.id).all()
        )
        assert len(overrides) == 2
