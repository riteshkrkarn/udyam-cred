"""Test suite for Stage 2 database models and relationships."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.models import (
    User,
    Shop,
    Application,
    Consent,
    Document,
    HouseholdData,
    Decision,
    Override,
    AuditLog,
    DataSource,
)
from app.utils import utcnow_naive


class TestApplicationModel:
    """Tests for Application model."""

    def test_create_application(self, db_session):
        """Test creating an application."""
        # Create a borrower user
        borrower = User(
            email="borrower@test.com",
            password_hash="hash123",
            role="borrower",
        )
        db_session.add(borrower)

        # Create a shop
        shop = Shop(
            shop_id=1,
            gstin="27AAGPT7202F1Z5",
            shop_name="Test Shop",
            shop_category="kirana",
            state_code="27",
        )
        db_session.add(shop)
        db_session.commit()

        # Create application
        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            purpose="Inventory expansion",
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        # Verify
        assert app.id is not None
        assert app.status == "pending"
        assert app.borrower_id == borrower.id
        assert app.shop_id == shop.id

    def test_application_cascade_delete(self, db_session):
        """Test that deleting application cascades to related entities."""
        # Setup
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        # Create application with related data
        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        app_id = app.id

        # Add consent, document, household data
        consent = Consent(
            application_id=app_id,
            text="Test consent",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)

        document = Document(
            application_id=app_id,
            document_type="bill",
            file_path="/data/doc.pdf",
        )
        db_session.add(document)

        household = HouseholdData(
            application_id=app_id,
            family_size=4,
            dependents=2,
            monthly_expenses=25000,
        )
        db_session.add(household)
        db_session.commit()

        # Delete application
        db_session.delete(app)
        db_session.commit()

        # Verify cascades
        assert db_session.query(Application).filter_by(id=app_id).first() is None
        assert (
            db_session.query(Consent).filter_by(application_id=app_id).first() is None
        )
        assert (
            db_session.query(Document).filter_by(application_id=app_id).first() is None
        )
        assert (
            db_session.query(HouseholdData).filter_by(application_id=app_id).first()
            is None
        )


class TestConsentModel:
    """Tests for Consent model."""

    def test_create_consent(self, db_session):
        """Test creating a consent record."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        consent_text = "I agree to share data"
        consent = Consent(
            application_id=app.id,
            text=consent_text,
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)
        db_session.commit()

        # Verify
        retrieved = db_session.query(Consent).filter_by(id=consent.id).first()
        assert retrieved is not None
        assert retrieved.text == consent_text
        assert retrieved.borrower_agreed is True
        assert retrieved.agreed_at is not None
        assert retrieved.withdrawn_at is None


class TestDocumentModel:
    """Tests for Document model."""

    def test_create_document(self, db_session):
        """Test creating a document record."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        doc = Document(
            application_id=app.id,
            document_type="purchase_bill",
            file_path="/data/documents/1/bill.pdf",
        )
        db_session.add(doc)
        db_session.commit()

        # Verify
        retrieved = db_session.query(Document).filter_by(id=doc.id).first()
        assert retrieved is not None
        assert retrieved.document_type == "purchase_bill"
        assert retrieved.file_path == "/data/documents/1/bill.pdf"


class TestHouseholdDataModel:
    """Tests for HouseholdData model."""

    def test_create_household_data(self, db_session):
        """Test creating household data."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        household = HouseholdData(
            application_id=app.id,
            family_size=5,
            dependents=3,
            monthly_expenses=30000,
            assets=200000,
            liabilities=50000,
        )
        db_session.add(household)
        db_session.commit()

        # Verify
        retrieved = (
            db_session.query(HouseholdData).filter_by(application_id=app.id).first()
        )
        assert retrieved is not None
        assert retrieved.family_size == 5
        assert retrieved.dependents == 3
        assert retrieved.monthly_expenses == 30000
        assert retrieved.assets == 200000
        assert retrieved.liabilities == 50000

    def test_household_data_unique_per_application(self, db_session):
        """Test that each application can have only one household_data record."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        h1 = HouseholdData(
            application_id=app.id,
            family_size=4,
            dependents=2,
            monthly_expenses=25000,
        )
        db_session.add(h1)
        db_session.commit()

        # Try to add another (should fail due to unique constraint)
        h2 = HouseholdData(
            application_id=app.id,
            family_size=5,
            dependents=3,
            monthly_expenses=30000,
        )
        db_session.add(h2)

        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestDecisionModel:
    """Tests for Decision model."""

    def test_create_decision(self, db_session):
        """Test creating a decision."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        reasons = ["verified_10_months", "good_agreement_score"]
        reasons_json = json.dumps(reasons)
        
        tranche_plan = [
            {
                "tranche_num": 1,
                "amount": 80000,
                "tenor_months": 12,
                "emi_count": 12,
            }
        ]
        tranche_plan_json = json.dumps(tranche_plan)

        decision = Decision(
            application_id=app.id,
            verdict="approved",
            tier=1,
            verified_months=10,
            source_agreement_score=0.85,
            tranche_plan_json=tranche_plan_json,
            reasons_json=reasons_json,
        )
        db_session.add(decision)
        db_session.commit()

        # Verify
        retrieved = db_session.query(Decision).filter_by(id=decision.id).first()
        assert retrieved is not None
        assert retrieved.verdict == "approved"
        assert retrieved.tier == 1
        assert retrieved.verified_months == 10
        assert retrieved.source_agreement_score == 0.85
        assert json.loads(retrieved.reasons_json) == reasons
        assert json.loads(retrieved.tranche_plan_json)[0]["amount"] == 80000


class TestOverrideModel:
    """Tests for Override model."""

    def test_create_override(self, db_session):
        """Test creating an override record."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        officer = User(email="officer@test.com", password_hash="hash", role="officer")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(officer)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        tranche_plan = [
            {
                "tranche_num": 1,
                "amount": 80000,
                "tenor_months": 12,
                "emi_count": 12,
            }
        ]
        tranche_plan_json = json.dumps(tranche_plan)

        decision = Decision(
            application_id=app.id,
            verdict="approved",
            tier=1,
            verified_months=10,
            source_agreement_score=0.85,
            tranche_plan_json=tranche_plan_json,
        )
        db_session.add(decision)
        db_session.commit()

        override = Override(
            decision_id=decision.id,
            officer_id=officer.id,
            old_loan_amount=80000,
            new_loan_amount=60000,
            reason="Customer requested conservative approach",
        )
        db_session.add(override)
        db_session.commit()

        # Verify
        retrieved = db_session.query(Override).filter_by(id=override.id).first()
        assert retrieved is not None
        assert retrieved.old_loan_amount == 80000
        assert retrieved.new_loan_amount == 60000
        assert "conservative" in retrieved.reason


class TestAuditLogModel:
    """Tests for AuditLog model."""

    def test_create_audit_log(self, db_session):
        """Test creating an audit log entry."""
        officer = User(email="officer@test.com", password_hash="hash", role="officer")
        db_session.add(officer)
        db_session.commit()

        log = AuditLog(
            entity_type="application",
            entity_id=1,
            action="created",
            officer_id=officer.id,
            details_json='{"status": "pending"}',
        )
        db_session.add(log)
        db_session.commit()

        # Verify
        retrieved = db_session.query(AuditLog).filter_by(id=log.id).first()
        assert retrieved is not None
        assert retrieved.entity_type == "application"
        assert retrieved.entity_id == 1
        assert retrieved.action == "created"
        assert retrieved.officer_id == officer.id


class TestDataSourceModel:
    """Tests for DataSource model."""

    def test_create_data_source(self, db_session):
        """Test creating a data source record."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        data_json = json.dumps(
            {
                "transactions": [
                    {"date": "2024-01-01", "amount": 5000},
                ],
            }
        )

        source = DataSource(
            application_id=app.id,
            source="upi",
            vintage_date=utcnow_naive(),
            data_hash="abc123def456",
            data_json=data_json,
        )
        db_session.add(source)
        db_session.commit()

        # Verify
        retrieved = db_session.query(DataSource).filter_by(id=source.id).first()
        assert retrieved is not None
        assert retrieved.source == "upi"
        assert retrieved.data_hash == "abc123def456"
        assert json.loads(retrieved.data_json)["transactions"][0]["amount"] == 5000


class TestModelRelationships:
    """Tests for model relationships."""

    def test_application_relationships(self, db_session):
        """Test application relationships work correctly."""
        borrower = User(email="borrower@test.com", password_hash="hash")
        shop = Shop(shop_id=1, shop_category="kirana")
        db_session.add(borrower)
        db_session.add(shop)
        db_session.commit()

        app = Application(
            borrower_id=borrower.id,
            shop_id=shop.id,
            loan_amount_requested=100000,
            status="pending",
        )
        db_session.add(app)
        db_session.commit()

        # Add related entities
        consent = Consent(
            application_id=app.id,
            text="Test",
            borrower_agreed=True,
            agreed_at=utcnow_naive(),
        )
        db_session.add(consent)

        decision = Decision(
            application_id=app.id,
            verdict="approved",
            tier=1,
            verified_months=10,
            source_agreement_score=0.80,
        )
        db_session.add(decision)
        db_session.commit()

        # Access through relationships
        assert len(app.consents) == 1
        assert len(app.decisions) == 1
        assert app.borrower.email == "borrower@test.com"
        assert app.shop.shop_id == 1

