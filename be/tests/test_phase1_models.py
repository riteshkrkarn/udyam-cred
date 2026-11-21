"""Tests for Phase 1 database models."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import (
    Tier,
    Photo,
    SourceAgreement,
    VerifiedWindow,
    GSTCoverage,
    Tranche,
    RepaymentRecord,
    StopRule,
    LocationVerification,
    RateEnvironment,
    Application,
    User,
    Shop,
)
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db():
    """Create a clean database for each test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db: Session):
    """Create a test user."""
    user = User(email="test@example.com", password_hash="hashed", role="borrower")
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def shop(db: Session):
    """Create a test shop."""
    shop = Shop(
        shop_id=1,
        gstin="18AABCC9054R1Z5",
        shop_name="Test Shop",
        shop_category="retail",
        state_code="MH",
        gstin_valid=True,
    )
    db.add(shop)
    db.commit()
    return shop


@pytest.fixture
def application(db: Session, user: User, shop: Shop):
    """Create a test application."""
    app = Application(
        borrower_id=user.id,
        shop_id=shop.id,
        loan_amount_requested=50000,
        purpose="Business expansion",
        status="pending",
    )
    db.add(app)
    db.commit()
    return app


class TestTierModel:
    def test_create_tier(self, db: Session):
        """Test creating a Tier."""
        tier = Tier(
            tier_id=1,
            name="Tier 1",
            min_verified_months=6,
            min_amount=10000,
            max_amount=50000,
            rate_adjustment=4.0,
            confidence_threshold=0.7,
        )
        db.add(tier)
        db.commit()

        fetched = db.query(Tier).filter_by(tier_id=1).first()
        assert fetched is not None
        assert fetched.name == "Tier 1"
        assert fetched.max_amount == 50000


class TestPhotoModel:
    def test_create_photo(self, db: Session, application: Application):
        """Test creating a Photo."""
        photo = Photo(
            application_id=application.id,
            photo_type="shop_front",
            photo_path="/path/to/photo.jpg",
            location_lat=12.9716,
            location_lng=77.5946,
            random_code_written="ABC123",
            verification_status="pending",
        )
        db.add(photo)
        db.commit()

        fetched = db.query(Photo).filter_by(application_id=application.id).first()
        assert fetched is not None
        assert fetched.photo_type == "shop_front"
        assert fetched.location_lat == 12.9716


class TestSourceAgreementModel:
    def test_create_source_agreement(self, db: Session, application: Application):
        """Test creating a SourceAgreement."""
        sa = SourceAgreement(
            application_id=application.id,
            aa_monthly_avg=80000,
            gst_monthly_avg=85000,
            upi_monthly_avg=120000,
            agreement_score_percent=0.82,
            weighted_sales=82500,
            sources_used="aa,gst,upi",
            confidence="medium",
        )
        db.add(sa)
        db.commit()

        fetched = (
            db.query(SourceAgreement)
            .filter_by(application_id=application.id)
            .first()
        )
        assert fetched is not None
        assert fetched.agreement_score_percent == 0.82


class TestVerifiedWindowModel:
    def test_create_verified_window(self, db: Session, application: Application):
        """Test creating a VerifiedWindow."""
        now = datetime.now()
        vw = VerifiedWindow(
            application_id=application.id,
            start_date=now,
            end_date=now + timedelta(days=180),
            months_verified=10,
            data_quality_score=0.85,
            weighted_importance=0.83,
        )
        db.add(vw)
        db.commit()

        fetched = (
            db.query(VerifiedWindow)
            .filter_by(application_id=application.id)
            .first()
        )
        assert fetched is not None
        assert fetched.months_verified == 10


class TestGSTCoverageModel:
    def test_create_gst_coverage(self, db: Session, application: Application):
        """Test creating a GSTCoverage."""
        gc = GSTCoverage(
            application_id=application.id,
            purchases_declared=500000,
            gst_turnover=520000,
            coverage_percent=1.04,
            reconciliation_flag=False,
            notes="Good alignment",
        )
        db.add(gc)
        db.commit()

        fetched = (
            db.query(GSTCoverage)
            .filter_by(application_id=application.id)
            .first()
        )
        assert fetched is not None
        assert fetched.coverage_percent == 1.04


class TestTrancheModel:
    def test_create_tranche(self, db: Session, application: Application):
        """Test creating a Tranche."""
        now = datetime.now()
        tranche = Tranche(
            application_id=application.id,
            tranche_num=1,
            amount=50000,
            release_date=now,
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db.add(tranche)
        db.commit()

        fetched = (
            db.query(Tranche)
            .filter(Tranche.application_id == application.id)
            .first()
        )
        assert fetched is not None
        assert fetched.amount == 50000


class TestRepaymentRecordModel:
    def test_create_repayment_record(self, db: Session, application: Application):
        """Test creating a RepaymentRecord."""
        now = datetime.now()
        tranche = Tranche(
            application_id=application.id,
            tranche_num=1,
            amount=50000,
            release_date=now,
            release_status="pending",
            emi_count=12,
            tenor_months=12,
        )
        db.add(tranche)
        db.flush()

        record = RepaymentRecord(
            tranche_id=tranche.id,
            emi_num=1,
            due_date=now + timedelta(days=30),
            amount=4200,
            payment_status="pending",
            days_late=0,
        )
        db.add(record)
        db.commit()

        fetched = (
            db.query(RepaymentRecord)
            .filter_by(emi_num=1)
            .first()
        )
        assert fetched is not None
        assert fetched.amount == 4200


class TestStopRuleModel:
    def test_create_stop_rule(self, db: Session, application: Application):
        """Test creating a StopRule."""
        now = datetime.now()
        stop_rule = StopRule(
            application_id=application.id,
            missed_emi_count=2,
            frozen_date=now,
            review_required=True,
            reason="2 EMIs missed",
        )
        db.add(stop_rule)
        db.commit()

        fetched = (
            db.query(StopRule)
            .filter_by(application_id=application.id)
            .first()
        )
        assert fetched is not None
        assert fetched.missed_emi_count == 2


class TestLocationVerificationModel:
    def test_create_location_verification(self, db: Session, application: Application):
        """Test creating a LocationVerification."""
        lv = LocationVerification(
            application_id=application.id,
            rent_address="123 Main St, Bangalore",
            shop_address="123 Main St, Bangalore",
            photo_location_lat=12.9716,
            photo_location_lng=77.5946,
            distance_meters=120,
            verified_bool=True,
        )
        db.add(lv)
        db.commit()

        fetched = (
            db.query(LocationVerification)
            .filter_by(application_id=application.id)
            .first()
        )
        assert fetched is not None
        assert fetched.verified_bool is True


class TestRateEnvironmentModel:
    def test_create_rate_environment(self, db: Session):
        """Test creating a RateEnvironment."""
        now = datetime.now()
        rate_env = RateEnvironment(
            rate_date=now,
            tier_1_industry_rate=14.5,
            tier_2_industry_rate=12.0,
            tier_3_industry_rate=10.5,
            source="manual",
        )
        db.add(rate_env)
        db.commit()

        fetched = db.query(RateEnvironment).first()
        assert fetched is not None
        assert fetched.tier_1_industry_rate == 14.5


class TestCascadeDeletes:
    def test_delete_application_deletes_photos(self, db: Session, application: Application):
        """Test that deleting an application deletes related photos."""
        photo = Photo(
            application_id=application.id,
            photo_type="shop_front",
            photo_path="/path/to/photo.jpg",
            verification_status="pending",
        )
        db.add(photo)
        db.commit()

        photo_id = photo.id
        db.delete(application)
        db.commit()

        fetched = db.query(Photo).filter_by(id=photo_id).first()
        assert fetched is None
