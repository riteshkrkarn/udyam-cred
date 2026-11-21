"""
Phase 1 test stubs for rate calculation.

Tests:
- Industry rate lookup
- Rate adjustment (+ or -) based on tier and risk profile
- Tenor and amount impact on final rate
"""
import pytest
from datetime import datetime

from sqlalchemy.orm import Session

from app.adapters.rate_adapter import RateAdapter
from app.engines.rate_calculation_engine import RateCalculationEngine
from app.models import RateEnvironment
from app.utils import utcnow_naive


class TestRateAdapterIntegration:
    """Test RateAdapter integration with RateCalculationEngine."""

    @pytest.fixture
    def setup_rates(self, db_session: Session):
        """Set up test industry rates in database."""
        rate_env = RateEnvironment(
            rate_date=utcnow_naive(),
            tier_1_industry_rate=14.5,
            tier_2_industry_rate=12.0,
            tier_3_industry_rate=10.5,
            source="test",
        )
        db_session.add(rate_env)
        db_session.commit()
        return rate_env

    def test_rate_adapter_get_tier_1_rate(self, db_session: Session, setup_rates):
        """Test fetching Tier 1 industry rate from adapter."""
        rate = RateAdapter.get_industry_rate(tier=1, db=db_session)
        assert rate == 14.5

    def test_rate_adapter_get_tier_2_rate(self, db_session: Session, setup_rates):
        """Test fetching Tier 2 industry rate from adapter."""
        rate = RateAdapter.get_industry_rate(tier=2, db=db_session)
        assert rate == 12.0

    def test_rate_adapter_get_tier_3_rate(self, db_session: Session, setup_rates):
        """Test fetching Tier 3 industry rate from adapter."""
        rate = RateAdapter.get_industry_rate(tier=3, db=db_session)
        assert rate == 10.5

    def test_rate_adapter_fallback_to_defaults(self, db_session: Session):
        """Test adapter falls back to default rates when no data in DB."""
        # Don't set up any rates
        rate_tier1 = RateAdapter.get_industry_rate(tier=1, db=db_session)
        rate_tier2 = RateAdapter.get_industry_rate(tier=2, db=db_session)
        rate_tier3 = RateAdapter.get_industry_rate(tier=3, db=db_session)

        assert rate_tier1 == 14.5  # DEFAULT_RATES[1]
        assert rate_tier2 == 12.0  # DEFAULT_RATES[2]
        assert rate_tier3 == 10.5  # DEFAULT_RATES[3]

    def test_rate_adapter_invalid_tier_raises_error(self, db_session: Session):
        """Test adapter raises ValueError for invalid tier."""
        with pytest.raises(ValueError, match="Invalid tier"):
            RateAdapter.get_industry_rate(tier=4, db=db_session)

        with pytest.raises(ValueError, match="Invalid tier"):
            RateAdapter.get_industry_rate(tier=0, db=db_session)

    def test_rate_adapter_set_and_retrieve_rates(self, db_session: Session):
        """Test setting and retrieving industry rates."""
        success = RateAdapter.set_industry_rates(
            tier_1=15.0,
            tier_2=13.0,
            tier_3=11.0,
            source="manual",
            db=db_session,
        )
        assert success is True

        # Retrieve and verify
        rate1 = RateAdapter.get_industry_rate(tier=1, db=db_session)
        rate2 = RateAdapter.get_industry_rate(tier=2, db=db_session)
        rate3 = RateAdapter.get_industry_rate(tier=3, db=db_session)

        assert rate1 == 15.0
        assert rate2 == 13.0
        assert rate3 == 11.0

    def test_rate_adapter_uses_latest_rate(self, db_session: Session):
        """Test adapter uses latest rate when multiple dates exist."""
        # First rate
        RateAdapter.set_industry_rates(
            tier_1=14.0, tier_2=12.0, tier_3=10.0, source="manual", db=db_session
        )
        # Second (newer) rate
        RateAdapter.set_industry_rates(
            tier_1=14.5, tier_2=12.5, tier_3=10.5, source="manual", db=db_session
        )

        # Should get the latest
        rate1 = RateAdapter.get_industry_rate(tier=1, db=db_session)
        assert rate1 == 14.5


class TestRateCalculationEngine:
    """Test RateCalculationEngine with tier adjustments."""

    @pytest.fixture
    def setup_rates(self, db_session: Session):
        """Set up test industry rates in database."""
        RateAdapter.set_industry_rates(
            tier_1=14.5,
            tier_2=12.0,
            tier_3=10.5,
            source="test",
            db=db_session,
        )

    def test_calculate_rate_tier_1(self, db_session: Session, setup_rates):
        """Test rate calculation for Tier 1 with adjustment."""
        result = RateCalculationEngine.calculate_rate(tier=1, db=db_session)

        assert result.industry_rate == 14.5
        assert result.tier_adjustment == 4.0
        assert result.final_rate == 18.5  # 14.5 + 4.0

    def test_calculate_rate_tier_2(self, db_session: Session, setup_rates):
        """Test rate calculation for Tier 2 with adjustment."""
        result = RateCalculationEngine.calculate_rate(tier=2, db=db_session)

        assert result.industry_rate == 12.0
        assert result.tier_adjustment == 2.0
        assert result.final_rate == 14.0  # 12.0 + 2.0

    def test_calculate_rate_tier_3(self, db_session: Session, setup_rates):
        """Test rate calculation for Tier 3 with no adjustment."""
        result = RateCalculationEngine.calculate_rate(tier=3, db=db_session)

        assert result.industry_rate == 10.5
        assert result.tier_adjustment == 0.0
        assert result.final_rate == 10.5  # 10.5 + 0.0

    def test_calculate_rate_invalid_tier(self, db_session: Session):
        """Test rate calculation with invalid tier returns zeros."""
        result = RateCalculationEngine.calculate_rate(tier=4, db=db_session)

        assert result.industry_rate == 0.0
        assert result.tier_adjustment == 0.0
        assert result.final_rate == 0.0

    def test_calculate_rate_applies_policy_adjustment(self, db_session: Session, setup_rates):
        """Test that tier adjustment is applied after fetching base rate."""
        # Verify tier 1: base 14.5 + policy adj 4.0 = 18.5
        result_t1 = RateCalculationEngine.calculate_rate(tier=1, db=db_session)
        assert result_t1.final_rate == 18.5

        # Verify tier 2: base 12.0 + policy adj 2.0 = 14.0
        result_t2 = RateCalculationEngine.calculate_rate(tier=2, db=db_session)
        assert result_t2.final_rate == 14.0

        # Verify tier 3: base 10.5 + policy adj 0.0 = 10.5
        result_t3 = RateCalculationEngine.calculate_rate(tier=3, db=db_session)
        assert result_t3.final_rate == 10.5

    def test_calculate_rate_with_specific_date(self, db_session: Session):
        """Test rate calculation with specific date parameter."""
        # Set initial rate on an earlier date
        earlier_env = RateEnvironment(
            rate_date=datetime(2024, 1, 1),
            tier_1_industry_rate=13.0,
            tier_2_industry_rate=11.0,
            tier_3_industry_rate=9.0,
            source="test",
        )
        db_session.add(earlier_env)
        db_session.commit()

        # Set newer rate
        RateAdapter.set_industry_rates(
            tier_1=15.0,
            tier_2=13.0,
            tier_3=11.0,
            source="test",
            db=db_session,
        )

        # Query with earlier date should get earlier rate
        result = RateCalculationEngine.calculate_rate(
            tier=1, db=db_session, rate_date=datetime(2024, 1, 15)
        )
        assert result.industry_rate == 13.0
        assert result.final_rate == 17.0  # 13.0 + 4.0 adjustment


class TestRateAuditLogging:
    """Test audit logging for rate calculations."""

    @pytest.fixture
    def setup_rates(self, db_session: Session):
        """Set up test industry rates in database."""
        RateAdapter.set_industry_rates(
            tier_1=14.5,
            tier_2=12.0,
            tier_3=10.5,
            source="test",
            db=db_session,
        )

    def test_rate_calculation_logs_audit_trail(self, db_session: Session, setup_rates, caplog):
        """Test that rate calculation logs audit trail with all components."""
        import logging

        caplog.set_level(logging.INFO)

        result = RateCalculationEngine.calculate_rate(tier=1, db=db_session)

        # Check that log message contains all required components
        log_records = [r for r in caplog.records if "Rate calculation" in r.message]
        assert len(log_records) > 0

        log_msg = log_records[0].message
        assert "tier=1" in log_msg
        assert "base_rate=14.5%" in log_msg
        assert "adjustment=4.0%" in log_msg
        assert "final_rate=18.5%" in log_msg

    def test_rate_calculation_logs_all_tiers(self, db_session: Session, setup_rates, caplog):
        """Test that rate calculation logs for all tiers include correct values."""
        import logging

        caplog.set_level(logging.INFO)

        # Calculate for each tier
        RateCalculationEngine.calculate_rate(tier=1, db=db_session)
        RateCalculationEngine.calculate_rate(tier=2, db=db_session)
        RateCalculationEngine.calculate_rate(tier=3, db=db_session)

        log_records = [r for r in caplog.records if "Rate calculation" in r.message]
        assert len(log_records) == 3

        # Verify tier 1 log
        tier1_msg = [r.message for r in log_records if "tier=1" in r.message][0]
        assert "final_rate=18.5%" in tier1_msg

        # Verify tier 2 log
        tier2_msg = [r.message for r in log_records if "tier=2" in r.message][0]
        assert "final_rate=14.0%" in tier2_msg

        # Verify tier 3 log
        tier3_msg = [r.message for r in log_records if "tier=3" in r.message][0]
        assert "final_rate=10.5%" in tier3_msg

    def test_rate_calculation_logs_invalid_tier_warning(self, db_session: Session, caplog):
        """Test that invalid tier requests are logged as warnings."""
        import logging

        caplog.set_level(logging.WARNING)

        RateCalculationEngine.calculate_rate(tier=4, db=db_session)

        warning_records = [
            r for r in caplog.records if "Invalid tier" in r.message
        ]
        assert len(warning_records) > 0

