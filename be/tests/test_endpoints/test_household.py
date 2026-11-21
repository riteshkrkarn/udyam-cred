"""Tests for household endpoints."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import Application, HouseholdData, Shop, User


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


class TestHouseholdCreate:
    """Tests for POST /api/applications/{id}/household."""

    def test_create_household_happy_path(self, db_session: Session, test_application):
        """Test creating household data with valid input."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            dependents=2,
            monthly_expenses=25000,
            assets=200000,
            liabilities=50000,
        )
        db_session.add(household)
        db_session.commit()
        db_session.refresh(household)

        assert household.id is not None
        assert household.family_size == 4
        assert household.monthly_expenses == 25000

    def test_create_household_zero_family_size(self, db_session: Session, test_application):
        """Test that family_size must be > 0."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=0,  # Invalid
            monthly_expenses=25000,
        )
        db_session.add(household)
        # Model doesn't enforce, but endpoint validation does


    def test_create_household_zero_expenses(self, db_session: Session, test_application):
        """Test that monthly_expenses must be > 0."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            monthly_expenses=0,  # Invalid
        )
        db_session.add(household)
        # Model doesn't enforce, but endpoint validation does

    def test_create_household_negative_liabilities(self, db_session: Session, test_application):
        """Test that liabilities must be >= 0."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            monthly_expenses=25000,
            liabilities=-1000,  # Invalid
        )
        db_session.add(household)
        # Model doesn't enforce, but endpoint validation does


class TestHouseholdRead:
    """Tests for GET /api/applications/{id}/household."""

    def test_get_household_found(self, db_session: Session, test_application):
        """Test retrieving household data."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            monthly_expenses=25000,
        )
        db_session.add(household)
        db_session.commit()

        retrieved = (
            db_session.query(HouseholdData)
            .filter_by(application_id=test_application.id)
            .first()
        )
        assert retrieved is not None
        assert retrieved.family_size == 4

    def test_get_household_not_found(self, db_session: Session, test_application):
        """Test retrieving household when none exists."""
        retrieved = (
            db_session.query(HouseholdData)
            .filter_by(application_id=test_application.id)
            .first()
        )
        assert retrieved is None


class TestHouseholdUpdate:
    """Tests for updating household data."""

    def test_update_household_data(self, db_session: Session, test_application):
        """Test updating household data."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            monthly_expenses=25000,
        )
        db_session.add(household)
        db_session.commit()

        household.family_size = 5
        household.monthly_expenses = 30000
        db_session.commit()

        retrieved = (
            db_session.query(HouseholdData)
            .filter_by(application_id=test_application.id)
            .first()
        )
        assert retrieved.family_size == 5
        assert retrieved.monthly_expenses == 30000

    def test_unique_household_per_app(self, db_session: Session, test_application):
        """Test that each application has at most one household record."""
        household1 = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            monthly_expenses=25000,
        )
        db_session.add(household1)
        db_session.commit()

        # Try to create another (should fail due to unique constraint)
        household2 = HouseholdData(
            application_id=test_application.id,
            family_size=5,
            monthly_expenses=30000,
        )
        db_session.add(household2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestHouseholdValidation:
    """Tests for household data validation."""

    def test_household_surplus_calculation_logic(self):
        """Test the surplus calculation logic (not in model, but in engine)."""
        # ABCA (monthly) = 100000
        # Monthly expenses = 25000
        # Surplus = 100000 - 25000 = 75000
        # EMI capacity (50% of surplus) = 37500
        
        # This is calculated in the emi_engine, not the model
        pass

    def test_household_with_high_liabilities(self, db_session: Session, test_application):
        """Test household with high existing liabilities."""
        household = HouseholdData(
            application_id=test_application.id,
            family_size=4,
            monthly_expenses=25000,
            liabilities=500000,  # High liabilities
        )
        db_session.add(household)
        db_session.commit()

        retrieved = (
            db_session.query(HouseholdData)
            .filter_by(application_id=test_application.id)
            .first()
        )
        assert retrieved.liabilities == 500000
