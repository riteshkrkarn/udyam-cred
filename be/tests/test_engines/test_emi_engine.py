"""Tests for EMI calculation engine."""
import pytest
from app.engines.emi_engine import calculate_household_surplus, calculate_emi_schedule


class TestHouseholdSurplus:
    """Test household surplus and EMI capacity calculation."""

    def test_typical_household(self):
        """Test typical household with positive surplus."""
        result = calculate_household_surplus(
            abca=50000,
            monthly_expenses=25000,
            existing_liabilities=36000,
        )

        # existing_emi = 36000 / 36 = 1000
        # surplus = 50000 - 25000 - 1000 = 24000
        # emi_capacity = 24000 * 0.5 = 12000
        assert result["household_surplus"] == pytest.approx(24000)
        assert result["emi_capacity"] == pytest.approx(12000)
        assert result["monthly_surplus_after_emi"] == pytest.approx(12000)

    def test_high_expenses_low_surplus(self):
        """Test household with high expenses and low surplus."""
        result = calculate_household_surplus(
            abca=30000,
            monthly_expenses=25000,
            existing_liabilities=12000,
        )

        # existing_emi = 12000 / 36 = 333.33
        # surplus = 30000 - 25000 - 333.33 = 4666.67
        # emi_capacity = 4666.67 * 0.5 = 2333.33
        assert result["household_surplus"] == pytest.approx(4666.67, rel=0.01)
        assert result["emi_capacity"] == pytest.approx(2333.33, rel=0.01)

    def test_zero_existing_liabilities(self):
        """Test household with no existing liabilities."""
        result = calculate_household_surplus(
            abca=40000,
            monthly_expenses=15000,
            existing_liabilities=0,
        )

        # surplus = 40000 - 15000 = 25000
        # emi_capacity = 25000 * 0.5 = 12500
        assert result["household_surplus"] == 25000
        assert result["emi_capacity"] == 12500

    def test_negative_surplus_clamped_to_zero(self):
        """Test that negative surplus is clamped to zero."""
        result = calculate_household_surplus(
            abca=20000,
            monthly_expenses=50000,
            existing_liabilities=0,
        )

        assert result["household_surplus"] == 0.0
        assert result["emi_capacity"] == 0.0

    def test_custom_emi_share(self):
        """Test custom EMI share percentage."""
        result = calculate_household_surplus(
            abca=50000,
            monthly_expenses=25000,
            existing_liabilities=0,
            emi_share=0.4,  # 40% instead of 50%
        )

        # surplus = 50000 - 25000 = 25000
        # emi_capacity = 25000 * 0.4 = 10000
        assert result["emi_capacity"] == 10000

    def test_high_existing_liabilities(self):
        """Test with high existing liabilities reducing surplus."""
        result = calculate_household_surplus(
            abca=60000,
            monthly_expenses=20000,
            existing_liabilities=360000,  # Very high liabilities
        )

        # existing_emi = 360000 / 36 = 10000
        # surplus = 60000 - 20000 - 10000 = 30000
        assert result["household_surplus"] == 30000


class TestEmiSchedule:
    """Test EMI schedule calculation."""

    def test_12_month_schedule(self):
        """Test standard 12-month EMI schedule."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=12,
        )

        assert len(schedule) == 12
        # Check first month
        assert schedule[0]["month"] == 1
        assert schedule[0]["emi"] > 0
        # Check last month balance is ~0
        assert schedule[-1]["balance"] == pytest.approx(0, abs=1)

    def test_24_month_schedule(self):
        """Test 24-month EMI schedule."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=24,
        )

        assert len(schedule) == 24
        assert schedule[-1]["balance"] == pytest.approx(0, abs=1)

    def test_36_month_schedule(self):
        """Test 36-month EMI schedule."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=36,
        )

        assert len(schedule) == 36
        assert schedule[-1]["balance"] == pytest.approx(0, abs=1)

    def test_emi_consistency(self):
        """Test that EMI is consistent across all months."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=12,
        )

        first_emi = schedule[0]["emi"]
        for month_data in schedule:
            assert month_data["emi"] == pytest.approx(first_emi, rel=0.01)

    def test_zero_interest_rate(self):
        """Test with zero interest rate."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=0.0,
            tenor_months=12,
        )

        # With 0% interest, EMI should be equal principal each month
        emi = 100000 / 12
        for month_data in schedule:
            assert month_data["emi"] == pytest.approx(emi)
            assert month_data["interest"] == pytest.approx(0)

    def test_balance_decreases(self):
        """Test that balance decreases each month."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=24,
        )

        for i in range(len(schedule) - 1):
            assert schedule[i + 1]["balance"] < schedule[i]["balance"]

    def test_principal_increases_with_months(self):
        """Test that principal component increases over time."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=24,
        )

        # In early months, more of EMI goes to interest
        # In later months, more of EMI goes to principal
        # So principal should generally increase over time
        early_months_principal = [schedule[i]["principal"] for i in range(3)]
        late_months_principal = [schedule[i]["principal"] for i in range(-3, 0)]
        
        assert sum(late_months_principal) > sum(early_months_principal)

    def test_zero_loan_amount(self):
        """Test with zero loan amount."""
        schedule = calculate_emi_schedule(
            loan_amount=0,
            rate_percent=12.0,
            tenor_months=12,
        )

        assert len(schedule) == 0

    def test_negative_loan_amount(self):
        """Test with negative loan amount."""
        schedule = calculate_emi_schedule(
            loan_amount=-100000,
            rate_percent=12.0,
            tenor_months=12,
        )

        assert len(schedule) == 0

    def test_negative_interest_rate(self):
        """Test with negative interest rate."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=-5.0,
            tenor_months=12,
        )

        assert len(schedule) == 0

    def test_zero_tenor(self):
        """Test with zero tenor."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=0,
        )

        assert len(schedule) == 0

    def test_total_principal_equals_loan(self):
        """Test that sum of principal payments equals loan amount."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=12.0,
            tenor_months=12,
        )

        total_principal = sum(m["principal"] for m in schedule)
        assert total_principal == pytest.approx(100000, rel=0.01)

    def test_high_interest_rate(self):
        """Test with high interest rate."""
        schedule = calculate_emi_schedule(
            loan_amount=100000,
            rate_percent=24.0,
            tenor_months=12,
        )

        # Higher interest rate should result in higher EMI
        first_emi = schedule[0]["emi"]
        assert first_emi > 100000 / 12  # More than simple division

    def test_large_loan_amount(self):
        """Test with large loan amount."""
        schedule = calculate_emi_schedule(
            loan_amount=500000,
            rate_percent=11.5,
            tenor_months=36,
        )

        assert len(schedule) == 36
        assert schedule[-1]["balance"] == pytest.approx(0, abs=1)
