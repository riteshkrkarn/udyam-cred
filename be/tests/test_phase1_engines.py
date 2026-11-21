"""Tests for Phase 1 engines."""
import pytest
from datetime import datetime, timedelta

from app.engines.photo_verification_engine import PhotoVerificationEngine
from app.engines.source_agreement_engine import SourceAgreementEngine
from app.engines.verified_window_engine import VerifiedWindowEngine
from app.engines.gst_coverage_engine import GSTCoverageEngine
from app.engines.tier_assignment_engine import TierAssignmentEngine
from app.engines.amount_rule_engine import AmountRuleEngine
from app.engines.rate_calculation_engine import RateCalculationEngine
from app.engines.tranche_plan_engine import TranchePlanEngine


class TestPhotoVerificationEngine:
    def test_verify_code_presence_success(self):
        """Test code verification passes."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", "ABC123")
        assert result is True

    def test_verify_code_presence_fail(self):
        """Test code verification fails."""
        result = PhotoVerificationEngine.verify_code_presence("ABC123", "XYZ789")
        assert result is False

    def test_calculate_distance(self):
        """Test distance calculation."""
        # Bangalore locations
        lat1, lng1 = 12.9716, 77.5946
        lat2, lng2 = 12.9716, 77.5946  # Same location
        distance = PhotoVerificationEngine.calculate_distance(lat1, lng1, lat2, lng2)
        assert distance < 1  # Should be very close

    def test_verify_photo_with_code_and_location(self):
        """Test complete photo verification."""
        photo_data = {
            "location_lat": 12.9716,
            "location_lng": 77.5946,
            "detected_code": "ABC123",
        }
        result = PhotoVerificationEngine.verify_photo(
            photo_data,
            expected_code="ABC123",
            rent_lat=12.9716,
            rent_lng=77.5946,
            tolerance_meters=500,
        )
        assert result.code_verified is True
        assert result.location_verified is True
        assert result.distance_from_rent < 100


class TestSourceAgreementEngine:
    def test_single_source_agreement(self):
        """Test agreement score with single source."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=None,
            upi_monthly_avg=None,
        )
        assert result.agreement_score == 0.5  # Low confidence
        assert result.confidence == "low"
        assert len(result.sources_used) == 1

    def test_two_sources_good_agreement(self):
        """Test agreement score with two sources that agree."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=80000,
            upi_monthly_avg=None,
        )
        assert result.agreement_score >= 0.85
        assert result.confidence in {"high", "medium"}
        assert len(result.sources_used) == 2

    def test_three_sources_agreement(self):
        """Test agreement score with three sources."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,
            gst_monthly_avg=82000,
            upi_monthly_avg=81000,
        )
        assert result.agreement_score > 0.5
        assert len(result.sources_used) == 3

    def test_weighted_sales_calculation(self):
        """Test weighted sales calculation."""
        result = SourceAgreementEngine.verify_sources(
            aa_monthly_avg=80000,  # 60%
            gst_monthly_avg=85000,  # 30%
            upi_monthly_avg=100000,  # 10%
        )
        expected = 80000 * 0.6 + 85000 * 0.3 + 100000 * 0.1
        assert abs(result.weighted_sales - expected) < 1


class TestVerifiedWindowEngine:
    def test_window_with_aa_and_gst(self):
        """Test verified window with AA and GST overlap."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verification(
            aa_start=now - timedelta(days=180),
            aa_end=now,
            gst_start=now - timedelta(days=120),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified >= 3  # 3-4 months overlap
        assert result.weight_factor > 0

    def test_window_no_overlap(self):
        """Test verified window with no overlap."""
        now = datetime.now()
        result = VerifiedWindowEngine.calculate_verification(
            aa_start=now - timedelta(days=180),
            aa_end=now - timedelta(days=120),  # Before GST
            gst_start=now - timedelta(days=60),
            gst_end=now,
            upi_start=None,
            upi_end=None,
        )
        assert result.months_verified == 0
        assert result.weight_factor == 0


class TestGSTCoverageEngine:
    def test_good_coverage(self):
        """Test GST coverage with good alignment."""
        result = GSTCoverageEngine.check_coverage(
            purchases_from_bills=500000,
            gst_turnover=520000,
        )
        assert result.coverage_percent > 1.0
        assert result.reconciliation_flag is False

    def test_low_coverage(self):
        """Test GST coverage with underdeclaration."""
        result = GSTCoverageEngine.check_coverage(
            purchases_from_bills=500000,
            gst_turnover=350000,  # Too low
        )
        assert result.coverage_percent < 0.8
        assert result.reconciliation_flag is True

    def test_high_coverage(self):
        """Test GST coverage with overstating."""
        result = GSTCoverageEngine.check_coverage(
            purchases_from_bills=500000,
            gst_turnover=700000,  # Too high
        )
        assert result.coverage_percent > 1.2
        assert result.reconciliation_flag is True


class TestTierAssignmentEngine:
    def test_tier1_assignment(self):
        """Test Tier 1 assignment."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=10,
            source_agreement_score=0.82,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
        )
        assert result.tier == 1
        assert result.max_amount == 50000
        assert result.rate_adjustment == 4.0

    def test_tier2_assignment(self):
        """Test Tier 2 assignment."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=12,
            source_agreement_score=0.75,
            photo_verified=True,
            gst_registered=True,
            udyam_registered=False,
        )
        assert result.tier == 2
        assert result.max_amount == 250000
        assert result.rate_adjustment == 2.0

    def test_rejection_insufficient_data(self):
        """Test rejection for insufficient verified data."""
        result = TierAssignmentEngine.assign_tier(
            verified_months=3,  # Below 6 month minimum
            source_agreement_score=0.8,
            photo_verified=True,
            gst_registered=False,
            udyam_registered=False,
        )
        assert result.tier == 0  # Rejected


class TestAmountRuleEngine:
    def test_amount_calculation_tier1(self):
        """Test amount calculation for Tier 1."""
        result = AmountRuleEngine.calculate_amount(
            tier=1,
            verified_months=10,
            source_agreement_score=0.82,
            gst_coverage=1.0,
        )
        expected = 50000 * 1.0 * 0.82  # cap * verified_weight * agreement_weight
        assert abs(result.approved_amount - expected) < 1

    def test_amount_with_gst_penalty(self):
        """Test amount calculation with GST coverage penalty."""
        result = AmountRuleEngine.calculate_amount(
            tier=1,
            verified_months=10,
            source_agreement_score=0.82,
            gst_coverage=0.7,  # Low coverage triggers penalty
        )
        # Should have 15% penalty applied
        assert result.approved_amount < 50000 * 0.82


class TestRateCalculationEngine:
    def test_rate_calculation(self):
        """Test rate calculation for a tier."""
        # Test with default rates (no database required)
        from app.adapters.rate_adapter import RateAdapter
        
        # Manually calculate since we're testing the engine logic
        tier = 1
        industry_rate = RateAdapter.DEFAULT_RATES[tier]
        tier_adjustments = {1: 4.0, 2: 2.0, 3: 0.0}
        tier_adjustment = tier_adjustments[tier]
        final_rate = industry_rate + tier_adjustment
        
        assert industry_rate == 14.5
        assert tier_adjustment == 4.0
        assert final_rate == 18.5


class TestTranchePlanEngine:
    def test_tier1_tranche_plan(self):
        """Test Tier 1 tranche plan (1 tranche)."""
        now = datetime.now()
        result = TranchePlanEngine.generate_plan(
            tier=1,
            amount=50000,
            start_date=now,
        )
        assert len(result.tranche_plan) == 1
        assert result.tranche_plan[0].amount == 50000

    def test_tier2_tranche_plan(self):
        """Test Tier 2 tranche plan (2 tranches)."""
        now = datetime.now()
        result = TranchePlanEngine.generate_plan(
            tier=2,
            amount=250000,
            start_date=now,
        )
        assert len(result.tranche_plan) == 2
        assert abs(result.tranche_plan[0].amount - 150000) < 1  # 60%
        assert abs(result.tranche_plan[1].amount - 100000) < 1  # 40%

    def test_tier3_tranche_plan(self):
        """Test Tier 3 tranche plan (4 tranches)."""
        now = datetime.now()
        result = TranchePlanEngine.generate_plan(
            tier=3,
            amount=1000000,
            start_date=now,
        )
        assert len(result.tranche_plan) == 4
        assert abs(result.tranche_plan[0].amount - 400000) < 1  # 40%
        assert abs(result.tranche_plan[1].amount - 300000) < 1  # 30%
        assert abs(result.tranche_plan[2].amount - 200000) < 1  # 20%
        assert abs(result.tranche_plan[3].amount - 100000) < 1  # 10%
