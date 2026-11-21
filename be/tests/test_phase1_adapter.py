"""Phase 1 tests for rate adapter and data source integrations.

Tests:
- get_industry_rate() returns correct values
- set_industry_rates() updates database
- Rate history tracking by date
- Default fallback rates
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.adapters.rate_adapter import RateAdapter
from app.models import RateEnvironment
from app.database import SessionLocal


class TestRateAdapter:
    """Test rate adapter functionality."""

    @pytest.fixture
    def session(self):
        """Create test database session."""
        session = SessionLocal()
        yield session
        session.close()

    def test_get_industry_rate_tier1(self, session):
        """Test fetch industry rate for Tier 1."""
        # Add a rate
        rate_env = RateEnvironment(
            rate_date=datetime.now(),
            tier_1_industry_rate=14.5,
            tier_2_industry_rate=12.0,
            tier_3_industry_rate=10.5,
            source="manual",
        )
        session.add(rate_env)
        session.commit()

        # Fetch rate
        rate = RateAdapter.get_industry_rate(session, tier=1)
        assert rate == 14.5

    def test_get_industry_rate_tier2(self, session):
        """Test fetch industry rate for Tier 2."""
        rate_env = RateEnvironment(
            rate_date=datetime.now(),
            tier_1_industry_rate=14.5,
            tier_2_industry_rate=12.0,
            tier_3_industry_rate=10.5,
            source="manual",
        )
        session.add(rate_env)
        session.commit()

        rate = RateAdapter.get_industry_rate(session, tier=2)
        assert rate == 12.0

    def test_get_industry_rate_tier3(self, session):
        """Test fetch industry rate for Tier 3."""
        rate_env = RateEnvironment(
            rate_date=datetime.now(),
            tier_1_industry_rate=14.5,
            tier_2_industry_rate=12.0,
            tier_3_industry_rate=10.5,
            source="manual",
        )
        session.add(rate_env)
        session.commit()

        rate = RateAdapter.get_industry_rate(session, tier=3)
        assert rate == 10.5

    def test_set_industry_rates_updates_database(self, session):
        """Test that set_industry_rates updates the database."""
        RateAdapter.set_industry_rates(
            session, tier_1=14.5, tier_2=12.0, tier_3=10.5, source="manual"
        )

        latest = (
            session.query(RateEnvironment).order_by(RateEnvironment.rate_date.desc())
        ).first()
        assert latest.tier_1_industry_rate == 14.5
        assert latest.tier_2_industry_rate == 12.0
        assert latest.tier_3_industry_rate == 10.5

    def test_rate_history_tracking_by_date(self, session):
        """Test rate history is tracked by date."""
        # Add first rate
        RateAdapter.set_industry_rates(
            session, tier_1=14.5, tier_2=12.0, tier_3=10.5, source="manual"
        )

        # Add second rate with different values
        yesterday = datetime.now() - timedelta(days=1)
        rate_env = RateEnvironment(
            rate_date=yesterday,
            tier_1_industry_rate=14.0,
            tier_2_industry_rate=11.5,
            tier_3_industry_rate=10.0,
            source="manual",
        )
        session.add(rate_env)
        session.commit()

        # Fetch latest rate
        latest = (
            session.query(RateEnvironment).order_by(RateEnvironment.rate_date.desc())
        ).first()
        assert latest.tier_1_industry_rate == 14.5  # Latest value

    def test_default_fallback_rates(self, session):
        """Test fallback rates when no rate exists."""
        # Clear all rates
        session.query(RateEnvironment).delete()
        session.commit()

        # Should return default
        rate = RateAdapter.get_industry_rate(session, tier=1, default=14.5)
        assert rate == 14.5

    def test_rate_adapter_returns_none_on_missing_and_no_default(self, session):
        """Test returns None when rate missing and no default."""
        session.query(RateEnvironment).delete()
        session.commit()

        rate = RateAdapter.get_industry_rate(session, tier=1, default=None)
        assert rate is None
