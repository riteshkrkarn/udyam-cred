"""Integration tests for Phase 1 scoring endpoint orchestration."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import (
    User,
    Application,
    Shop,
    Consent,
    HouseholdData,
    Photo,
    Decision,
)
from app.endpoints.scoring import _orchestrate_scoring


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    from app.database import SessionLocal
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db_session: Session):
    """Create a test borrower user."""
    user = User(
        email="borrower@test.com",
        password_hash="hashed_password",
        role="borrower",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def shop(db_session: Session):
    """Create a test shop with data."""
    shop = Shop(
        shop_id=1001,
        gstin="29ABCDE1234F1Z5",
        shop_name="Test Shop",
        shop_category="kirana",
        state_code="29",
        gstin_valid=True,
        upi_turnover=50000.0,
        gst_turnover=60000.0,
        purchases=40000.0,
        inventory_value=15000.0,
        cash_sales=5000.0,
    )
    db_session.add(shop)
    db_session.commit()
    return shop


@pytest.fixture
def application(db_session: Session, user: User, shop: Shop):
    """Create a test application."""
    app = Application(
        borrower_id=user.id,
        shop_id=shop.id,
        loan_amount_requested=50000.0,
        purpose="Stock replenishment",
        status="pending",
    )
    db_session.add(app)
    db_session.commit()

    # Add consent
    consent = Consent(
        application_id=app.id,
        text="I consent to sharing my data",
        borrower_agreed=True,
        agreed_at=datetime.now(),
    )
    db_session.add(consent)

    # Add household data
    household = HouseholdData(
        application_id=app.id,
        family_size=4,
        dependents=2,
        monthly_expenses=20000.0,
        assets=50000.0,
        liabilities=5000.0,
    )
    db_session.add(household)

    # Add verified photo
    photo = Photo(
        application_id=app.id,
        photo_type="shop_front",
        photo_path="/photos/shop1.jpg",
        location_lat=12.9716,
        location_lng=77.5946,
        timestamp=datetime.now(),
        random_code_written="CODE123",
        verification_status="verified",
        verified_at=datetime.now(),
    )
    db_session.add(photo)

    db_session.commit()
    return app


class TestScoringHappyPath:
    """Test happy path: all data present, all engines fire."""

    def test_happy_path_scoring(self, db_session: Session, application: Application):
        """
        Happy path: all data present, all engines fire successfully.
        
        - AA data available
        - GST data available
        - UPI data available
        - Verified window >= 6 months
        - Photos verified
        - Tier 1 or higher assigned
        - Amount approved
        """
        # Mock adapter responses by patching
        from unittest.mock import patch
        
        with patch('app.adapters.account_aggregator_adapter.AccountAggregatorAdapter.get_aa_data') as mock_aa:
            with patch('app.adapters.gst_adapter.GSTAdapter.get_gst_data') as mock_gst:
                with patch('app.adapters.upi_adapter.UPIAdapter.get_upi_data') as mock_upi:
                    with patch('app.adapters.rate_adapter.RateAdapter.get_industry_rate') as mock_rate:
                        # Set up mock data
                        now = datetime.now()
                        past_12_months = now - timedelta(days=365)
                        
                        mock_aa.return_value = {
                            "monthly_average": 5000.0,
                            "period_start": past_12_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_gst.return_value = {
                            "monthly_average": 5500.0,
                            "period_start": past_12_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_upi.return_value = {
                            "monthly_average": 4800.0,
                            "period_start": past_12_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_rate.return_value = 14.5  # Industry rate
                        
                        # Run orchestration
                        result = _orchestrate_scoring(
                            application=application,
                            family_size=4,
                            monthly_expenses=20000.0,
                            db=db_session,
                        )
                        
                        # Assertions
                        assert result["decision_id"] is not None
                        assert result["tier"] in [1, 2, 3]
                        assert result["approved_amount"] > 0
                        assert result["rate"] > 0
                        assert result["verified_months"] >= 6
                        assert result["location_verified"] is True
                        assert result["photo_count"] >= 1
                        assert len(result["reasons"]) > 0
                        assert result["source_agreement"] > 0.5
                        assert len(result["tranche_plan"]) > 0


class TestScoringEdgeCases:
    """Test edge cases and error scenarios."""

    def test_missing_aa_data(self, db_session: Session, application: Application):
        """
        Edge case: missing AA data.
        
        Should continue with GST+UPI only, lower confidence.
        """
        from unittest.mock import patch
        
        with patch('app.adapters.account_aggregator_adapter.AccountAggregatorAdapter.get_aa_data') as mock_aa:
            with patch('app.adapters.gst_adapter.GSTAdapter.get_gst_data') as mock_gst:
                with patch('app.adapters.upi_adapter.UPIAdapter.get_upi_data') as mock_upi:
                    with patch('app.adapters.rate_adapter.RateAdapter.get_industry_rate') as mock_rate:
                        now = datetime.now()
                        past_6_months = now - timedelta(days=180)
                        
                        # AA data missing (raise exception)
                        mock_aa.side_effect = Exception("AA data not available")
                        
                        mock_gst.return_value = {
                            "monthly_average": 5500.0,
                            "period_start": past_6_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_upi.return_value = {
                            "monthly_average": 4800.0,
                            "period_start": past_6_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_rate.return_value = 14.5
                        
                        # Run orchestration
                        result = _orchestrate_scoring(
                            application=application,
                            family_size=4,
                            monthly_expenses=20000.0,
                            db=db_session,
                        )
                        
                        # Should complete with lower confidence
                        assert result["decision_id"] is not None
                        # Verified months should be based on GST+UPI overlap
                        assert result["verified_months"] >= 0

    def test_insufficient_verified_months(self, db_session: Session):
        """
        Edge case: insufficient verified months (< 6).
        
        Should reject or assign Tier 0.
        """
        from unittest.mock import patch
        
        # Create user and shop
        user = User(
            email="test2@test.com",
            password_hash="hashed",
            role="borrower",
        )
        db_session.add(user)
        
        shop = Shop(
            shop_id=2001,
            gstin="29ABCDE1234F1Z5",
            shop_name="Test Shop 2",
            shop_category="kirana",
            state_code="29",
            gstin_valid=True,
            upi_turnover=50000.0,
            gst_turnover=60000.0,
            purchases=40000.0,
            inventory_value=15000.0,
            cash_sales=5000.0,
        )
        db_session.add(shop)
        db_session.commit()
        
        # Create application
        app = Application(
            borrower_id=user.id,
            shop_id=shop.id,
            loan_amount_requested=50000.0,
            purpose="Stock replenishment",
            status="pending",
        )
        db_session.add(app)
        db_session.commit()
        
        with patch('app.adapters.account_aggregator_adapter.AccountAggregatorAdapter.get_aa_data') as mock_aa:
            with patch('app.adapters.gst_adapter.GSTAdapter.get_gst_data') as mock_gst:
                with patch('app.adapters.upi_adapter.UPIAdapter.get_upi_data') as mock_upi:
                    with patch('app.adapters.rate_adapter.RateAdapter.get_industry_rate') as mock_rate:
                        now = datetime.now()
                        only_2_months = now - timedelta(days=60)
                        
                        # Only 2 months of verified data
                        mock_aa.return_value = {
                            "monthly_average": 5000.0,
                            "period_start": only_2_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_gst.return_value = {
                            "monthly_average": 5500.0,
                            "period_start": only_2_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_upi.return_value = None  # No UPI data
                        mock_rate.return_value = 14.5
                        
                        result = _orchestrate_scoring(
                            application=app,
                            family_size=4,
                            monthly_expenses=20000.0,
                            db=db_session,
                        )
                        
                        # Should have insufficient verified months
                        assert result["verified_months"] < 6
                        # Tier should be 0 (rejected)
                        assert result["tier"] == 0

    def test_no_gst_registration(self, db_session: Session):
        """
        Edge case: no GST registration, GSTCoverageEngine should be skipped.
        
        Should still work with AA+UPI only, assign Tier 1.
        """
        from unittest.mock import patch
        
        # Create user and shop without GST
        user = User(
            email="test3@test.com",
            password_hash="hashed",
            role="borrower",
        )
        db_session.add(user)
        
        shop_no_gst = Shop(
            shop_id=3001,
            gstin=None,
            shop_name="Test Shop No GST",
            shop_category="kirana",
            state_code="29",
            gstin_valid=False,
            upi_turnover=50000.0,
            gst_turnover=0.0,
            purchases=40000.0,
            inventory_value=15000.0,
            cash_sales=5000.0,
        )
        db_session.add(shop_no_gst)
        db_session.commit()
        
        # Create application
        app = Application(
            borrower_id=user.id,
            shop_id=shop_no_gst.id,
            loan_amount_requested=50000.0,
            purpose="Stock replenishment",
            status="pending",
        )
        db_session.add(app)
        db_session.commit()
        
        # Add verified photo
        photo = Photo(
            application_id=app.id,
            photo_type="shop_front",
            photo_path="/photos/shop3.jpg",
            location_lat=12.9716,
            location_lng=77.5946,
            timestamp=datetime.now(),
            random_code_written="CODE123",
            verification_status="verified",
            verified_at=datetime.now(),
        )
        db_session.add(photo)
        db_session.commit()
        
        with patch('app.adapters.account_aggregator_adapter.AccountAggregatorAdapter.get_aa_data') as mock_aa:
            with patch('app.adapters.gst_adapter.GSTAdapter.get_gst_data') as mock_gst:
                with patch('app.adapters.upi_adapter.UPIAdapter.get_upi_data') as mock_upi:
                    with patch('app.adapters.rate_adapter.RateAdapter.get_industry_rate') as mock_rate:
                        now = datetime.now()
                        past_6_months = now - timedelta(days=180)
                        
                        mock_aa.return_value = {
                            "monthly_average": 5000.0,
                            "period_start": past_6_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        # GST not registered
                        mock_gst.return_value = None
                        
                        mock_upi.return_value = {
                            "monthly_average": 4800.0,
                            "period_start": past_6_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_rate.return_value = 14.5
                        
                        result = _orchestrate_scoring(
                            application=app,
                            family_size=4,
                            monthly_expenses=20000.0,
                            db=db_session,
                        )
                        
                        # Should work without GST coverage engine
                        assert result["decision_id"] is not None
                        assert result["tier"] >= 1  # Should get Tier 1 at least
                        # Reasons should NOT mention GST coverage since not registered
                        assert not any("gst_coverage" in str(r) for r in result["reasons"])


class TestScoringDatabasePersistence:
    """Test that decisions are properly saved to database."""

    def test_decision_saved_to_db(self, db_session: Session, application: Application):
        """Decision should be saved to Decision table with all fields."""
        from unittest.mock import patch
        
        with patch('app.adapters.account_aggregator_adapter.AccountAggregatorAdapter.get_aa_data') as mock_aa:
            with patch('app.adapters.gst_adapter.GSTAdapter.get_gst_data') as mock_gst:
                with patch('app.adapters.upi_adapter.UPIAdapter.get_upi_data') as mock_upi:
                    with patch('app.adapters.rate_adapter.RateAdapter.get_industry_rate') as mock_rate:
                        now = datetime.now()
                        past_12_months = now - timedelta(days=365)
                        
                        mock_aa.return_value = {
                            "monthly_average": 5000.0,
                            "period_start": past_12_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_gst.return_value = {
                            "monthly_average": 5500.0,
                            "period_start": past_12_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_upi.return_value = {
                            "monthly_average": 4800.0,
                            "period_start": past_12_months.isoformat(),
                            "period_end": now.isoformat(),
                        }
                        
                        mock_rate.return_value = 14.5
                        
                        # Run orchestration
                        result = _orchestrate_scoring(
                            application=application,
                            family_size=4,
                            monthly_expenses=20000.0,
                            db=db_session,
                        )
                        
                        # Fetch decision from database
                        decision = db_session.query(Decision).filter_by(
                            id=result["decision_id"]
                        ).first()
                        
                        assert decision is not None
                        assert decision.tier == result["tier"]
                        assert decision.verified_months == result["verified_months"]
                        assert decision.source_agreement == result["source_agreement"]
                        assert decision.location_verified == result["location_verified"]
                        assert decision.photo_count == result["photo_count"]
                        assert decision.approved_amount == result["approved_amount"]
                        assert decision.rate_percent == result["rate"]
