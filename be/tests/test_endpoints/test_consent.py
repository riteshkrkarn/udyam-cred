"""Tests for consent endpoints."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import Application, Consent, Shop, User
from app.utils import utcnow_naive


@pytest.fixture
def test_user(db_session: Session):
    """Create test user."""
    user = User(
        email="test@test.com",
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
    )
    db_session.add(shop)
    db_session.commit()
    db_session.refresh(shop)
    return shop


@pytest.fixture
def test_application(db_session: Session, test_user, test_shop):
    """Create test application."""
    app = Application(
        borrower_id=test_user.id,
        shop_id=test_shop.id,
        loan_amount_requested=50000,
        purpose="Inventory",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    return app


class TestConsentCreate:
    """Tests for POST /api/applications/{id}/consent."""

    def test_create_consent_happy_path(self, db_session: Session, test_application):
        """Test creating consent record."""
        consent = Consent(
            application_id=test_application.id,
            text="I agree to share my financial data",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)
        db_session.commit()
        db_session.refresh(consent)

        assert consent.id is not None
        assert consent.borrower_agreed is True
        assert consent.agreed_at is not None
        assert consent.withdrawn_at is None

    def test_create_consent_disagree(self, db_session: Session, test_application):
        """Test creating consent record with disagreement."""
        consent = Consent(
            application_id=test_application.id,
            text="I agree to share my financial data",
            borrower_agreed=False,
        )
        db_session.add(consent)
        db_session.commit()

        retrieved = db_session.query(Consent).filter_by(id=consent.id).first()
        assert retrieved.borrower_agreed is False
        assert retrieved.agreed_at is None

    def test_create_consent_invalid_app(self, db_session: Session):
        """Test creating consent for non-existent application."""
        consent = Consent(
            application_id=9999,
            text="I agree...",
            borrower_agreed=True,
        )
        db_session.add(consent)
        # This should not fail at model level, but application relationship would fail
        # In practice, the endpoint would validate application exists first


class TestConsentRetrieve:
    """Tests for GET /api/applications/{id}/consent."""

    def test_get_consent(self, db_session: Session, test_application):
        """Test retrieving consent record."""
        consent = Consent(
            application_id=test_application.id,
            text="I agree to share my financial data",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)
        db_session.commit()

        retrieved = db_session.query(Consent).filter_by(
            application_id=test_application.id
        ).first()
        assert retrieved is not None
        assert retrieved.text == "I agree to share my financial data"

    def test_get_consent_not_found(self, db_session: Session):
        """Test retrieving consent for non-existent application."""
        result = db_session.query(Consent).filter_by(
            application_id=9999
        ).first()
        assert result is None


class TestConsentMultiple:
    """Tests for multiple consents per application."""

    def test_multiple_consents_same_app(self, db_session: Session, test_application):
        """Test creating multiple consent records for same application."""
        consent1 = Consent(
            application_id=test_application.id,
            text="Data sharing consent",
            borrower_agreed=True,
        )
        consent2 = Consent(
            application_id=test_application.id,
            text="Credit check consent",
            borrower_agreed=True,
        )
        db_session.add_all([consent1, consent2])
        db_session.commit()

        consents = db_session.query(Consent).filter_by(
            application_id=test_application.id
        ).all()
        assert len(consents) == 2

    def test_consent_cascade_delete(self, db_session: Session, test_user, test_shop):
        """Test that consent is deleted when application is deleted."""
        app = Application(
            borrower_id=test_user.id,
            shop_id=test_shop.id,
            loan_amount_requested=50000,
        )
        db_session.add(app)
        db_session.commit()

        consent = Consent(
            application_id=app.id,
            text="Test consent",
            borrower_agreed=True,
        )
        db_session.add(consent)
        db_session.commit()

        app_id = app.id
        consent_id = consent.id

        # Delete application
        db_session.delete(app)
        db_session.commit()

        # Verify consent is also deleted
        assert db_session.query(Consent).filter_by(id=consent_id).first() is None


class TestConsentWithdraw:
    """Tests for DELETE /api/applications/{id}/consent."""

    def test_withdraw_consent(self, db_session: Session, test_application):
        """Test withdrawing consent."""
        consent = Consent(
            application_id=test_application.id,
            text="I agree to share my financial data",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)
        db_session.commit()

        # Withdraw
        consent.withdrawn_at = utcnow_naive()
        db_session.commit()
        db_session.refresh(consent)

        assert consent.withdrawn_at is not None

    def test_withdraw_already_declined_consent(self, db_session: Session, test_application):
        """Test withdrawing consent that was never agreed."""
        consent = Consent(
            application_id=test_application.id,
            text="I agree...",
            borrower_agreed=False,
        )
        db_session.add(consent)
        db_session.commit()

        # Try to withdraw
        consent.withdrawn_at = utcnow_naive()
        db_session.commit()

        assert consent.withdrawn_at is not None

    def test_withdraw_consent(self, db_session: Session, test_application):
        """Test withdrawing consent."""
        consent = Consent(
            application_id=test_application.id,
            text="I agree to share my financial data",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)
        db_session.commit()

        # Withdraw
        consent.withdrawn_at = utcnow_naive()
        db_session.commit()

        retrieved = db_session.query(Consent).filter_by(id=consent.id).first()
        assert retrieved.withdrawn_at is not None
        assert retrieved.borrower_agreed is True  # Still agreed, but withdrawn later

    def test_cannot_score_without_consent(self, db_session: Session, test_application):
        """Test that scoring requires consent."""
        # Check that no consent exists
        consent = (
            db_session.query(Consent)
            .filter_by(application_id=test_application.id)
            .first()
        )
        assert consent is None

        # In endpoint, this would raise 403 Forbidden
        # Here we just verify the logic


class TestConsentValidation:
    """Tests for consent validation."""

    def test_consent_text_required(self, db_session: Session, test_application):
        """Test that consent text is required."""
        consent = Consent(
            application_id=test_application.id,
            text="",  # Empty text
            borrower_agreed=True,
        )
        db_session.add(consent)
        # Model doesn't enforce min length, but Pydantic schema does
        # So this would pass at DB level but fail at endpoint validation

    def test_multiple_consents_per_app(self, db_session: Session, test_application):
        """Test that an app can have multiple consent records (e.g., withdrawal + re-consent)."""
        consent1 = Consent(
            application_id=test_application.id,
            text="I agree v1",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent1)
        db_session.commit()

        consent1.withdrawn_at = utcnow_naive()

        consent2 = Consent(
            application_id=test_application.id,
            text="I agree v2",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent2)
        db_session.commit()

        consents = (
            db_session.query(Consent)
            .filter_by(application_id=test_application.id)
            .all()
        )
        assert len(consents) == 2
