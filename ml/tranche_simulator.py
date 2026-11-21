"""
Simulate repayment outcomes for tranches.

Models EMI payment patterns (on-time, late, missed) based on tier and health.
Used for evaluating tranche gates effectiveness vs single-amount loans.
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class EMI:
    """Single EMI record."""
    emi_num: int
    due_date: datetime
    amount: float
    principal: float
    interest: float
    payment_status: str  # ontime, late, missed, bounced
    paid_date: datetime = None
    days_late: int = 0


@dataclass
class TrancheOutcome:
    """Simulated outcome for a single tranche."""
    application_id: str
    tranche_num: int
    tranche_amount: float
    emi_schedule: List[EMI]
    total_paid: float
    total_missed: float
    completed_all_emis: bool
    missed_emi_count: int
    eligible_for_next_tranche: bool  # missed_emi_count < 2
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'application_id': self.application_id,
            'tranche_num': self.tranche_num,
            'tranche_amount': round(self.tranche_amount, 0),
            'emi_count': len(self.emi_schedule),
            'total_paid': round(self.total_paid, 0),
            'total_missed': round(self.total_missed, 0),
            'completed_all_emis': self.completed_all_emis,
            'missed_emi_count': self.missed_emi_count,
            'eligible_for_next_tranche': self.eligible_for_next_tranche,
            'emi_schedule': [
                {
                    'emi_num': e.emi_num,
                    'due_date': e.due_date.isoformat(),
                    'amount': round(e.amount, 0),
                    'status': e.payment_status,
                    'days_late': e.days_late
                }
                for e in self.emi_schedule
            ]
        }


class TrancheSimulator:
    """Simulate repayment outcomes for tranches."""
    
    # Payment probability models (by health and tier)
    PAYMENT_PROBABILITIES = {
        # Tier 1 (highest risk: new, no history)
        ('tier_1', 'poor'): {'ontime': 0.70, 'late': 0.15, 'missed': 0.10, 'bounced': 0.05},
        ('tier_1', 'fair'): {'ontime': 0.80, 'late': 0.12, 'missed': 0.06, 'bounced': 0.02},
        ('tier_1', 'good'): {'ontime': 0.88, 'late': 0.08, 'missed': 0.03, 'bounced': 0.01},
        ('tier_1', 'excellent'): {'ontime': 0.92, 'late': 0.05, 'missed': 0.02, 'bounced': 0.01},
        
        # Tier 2 (medium risk: some history)
        ('tier_2', 'poor'): {'ontime': 0.75, 'late': 0.12, 'missed': 0.08, 'bounced': 0.05},
        ('tier_2', 'fair'): {'ontime': 0.85, 'late': 0.08, 'missed': 0.05, 'bounced': 0.02},
        ('tier_2', 'good'): {'ontime': 0.90, 'late': 0.06, 'missed': 0.03, 'bounced': 0.01},
        ('tier_2', 'excellent'): {'ontime': 0.94, 'late': 0.04, 'missed': 0.01, 'bounced': 0.01},
        
        # Tier 3 (lowest risk: established, prior repayment)
        ('tier_3', 'poor'): {'ontime': 0.80, 'late': 0.10, 'missed': 0.07, 'bounced': 0.03},
        ('tier_3', 'fair'): {'ontime': 0.88, 'late': 0.06, 'missed': 0.04, 'bounced': 0.02},
        ('tier_3', 'good'): {'ontime': 0.93, 'late': 0.04, 'missed': 0.02, 'bounced': 0.01},
        ('tier_3', 'excellent'): {'ontime': 0.96, 'late': 0.03, 'missed': 0.01, 'bounced': 0.00},
    }
    
    def __init__(self, random_seed: int = 42):
        """Initialize simulator."""
        random.seed(random_seed)
        logger.info("Initialized tranche simulator")
    
    def calculate_emi(self, principal: float, annual_rate: float, months: int) -> float:
        """
        Calculate monthly EMI.
        
        EMI = P × [r(1+r)^n] / [(1+r)^n - 1]
        
        Args:
            principal: Loan amount (₹)
            annual_rate: Annual interest rate (%)
            months: Tenure in months
            
        Returns:
            Monthly EMI (₹)
        """
        monthly_rate = annual_rate / 12 / 100
        
        if monthly_rate == 0:
            return principal / months
        
        numerator = monthly_rate * (1 + monthly_rate) ** months
        denominator = (1 + monthly_rate) ** months - 1
        
        emi = principal * (numerator / denominator)
        return round(emi, 0)
    
    def generate_emi_schedule(self, 
                             principal: float,
                             annual_rate: float,
                             months: int,
                             start_date: datetime) -> List[EMI]:
        """
        Generate EMI schedule for a tranche.
        
        Args:
            principal: Tranche amount (₹)
            annual_rate: Annual rate (%)
            months: Tenure in months
            start_date: First EMI due date
            
        Returns:
            List of EMI records
        """
        emi_amount = self.calculate_emi(principal, annual_rate, months)
        total_interest = (emi_amount * months) - principal
        
        schedule = []
        remaining_principal = principal
        
        for month in range(1, months + 1):
            interest = total_interest / months
            principal_part = emi_amount - interest
            
            due_date = start_date + timedelta(days=30 * month)
            
            emi = EMI(
                emi_num=month,
                due_date=due_date,
                amount=emi_amount,
                principal=principal_part,
                interest=interest,
                payment_status='pending'
            )
            
            schedule.append(emi)
            remaining_principal -= principal_part
        
        return schedule
    
    def simulate_payment_pattern(self,
                                tier: str,
                                health: str,
                                emi_schedule: List[EMI]) -> Tuple[List[EMI], int]:
        """
        Simulate payment outcomes for an EMI schedule.
        
        Args:
            tier: 'tier_1', 'tier_2', or 'tier_3'
            health: 'poor', 'fair', 'good', or 'excellent'
            emi_schedule: List of EMI records (will be modified)
            
        Returns:
            Tuple of (modified schedule, missed_emi_count)
        """
        key = (tier, health)
        probs = self.PAYMENT_PROBABILITIES.get(key, self.PAYMENT_PROBABILITIES[('tier_1', 'fair')])
        
        missed_count = 0
        
        for emi in emi_schedule:
            # Sample payment status
            status = random.choices(
                list(probs.keys()),
                weights=list(probs.values()),
                k=1
            )[0]
            
            emi.payment_status = status
            
            if status == 'ontime':
                emi.paid_date = emi.due_date - timedelta(days=random.randint(1, 5))
                emi.days_late = 0
            
            elif status == 'late':
                days_late = random.expovariate(1.0 / 10)  # exponential with scale 10
                emi.days_late = int(max(1, min(days_late, 30)))  # 1-30 days late
                emi.paid_date = emi.due_date + timedelta(days=emi.days_late)
            
            elif status == 'missed':
                emi.paid_date = None
                emi.days_late = 999  # Flag as missed
                missed_count += 1
            
            elif status == 'bounced':
                # Treated as missed (not paid, check bounced)
                emi.paid_date = None
                emi.days_late = 999
                missed_count += 1
        
        return emi_schedule, missed_count
    
    def simulate_tranche(self,
                        application_id: str,
                        tranche_num: int,
                        tranche_amount: float,
                        annual_rate: float,
                        tenure_months: int,
                        tier: str,
                        health: str,
                        start_date: datetime) -> TrancheOutcome:
        """
        Simulate complete repayment outcome for a tranche.
        
        Args:
            application_id: Application ID
            tranche_num: Tranche number (1, 2, ...)
            tranche_amount: Tranche disbursement (₹)
            annual_rate: Annual interest rate (%)
            tenure_months: Months to repay
            tier: 'tier_1', 'tier_2', or 'tier_3'
            health: 'poor', 'fair', 'good', or 'excellent'
            start_date: First EMI due date
            
        Returns:
            TrancheOutcome with simulated repayment
        """
        # Generate EMI schedule
        schedule = self.generate_emi_schedule(
            tranche_amount, annual_rate, tenure_months, start_date
        )
        
        # Simulate payment pattern
        schedule, missed_count = self.simulate_payment_pattern(tier, health, schedule)
        
        # Calculate totals
        total_paid = sum(emi.amount for emi in schedule if emi.paid_date)
        total_missed = sum(emi.amount for emi in schedule if not emi.paid_date)
        completed_all = (missed_count == 0)
        
        # Tranche gate: eligible if < 2 EMIs missed
        eligible_for_next = (missed_count < 2)
        
        return TrancheOutcome(
            application_id=application_id,
            tranche_num=tranche_num,
            tranche_amount=tranche_amount,
            emi_schedule=schedule,
            total_paid=total_paid,
            total_missed=total_missed,
            completed_all_emis=completed_all,
            missed_emi_count=missed_count,
            eligible_for_next_tranche=eligible_for_next
        )
    
    def simulate_full_loan(self,
                          application_id: str,
                          tier: str,
                          total_amount: float,
                          rate: float,
                          health: str) -> List[TrancheOutcome]:
        """
        Simulate all tranches for a loan.
        
        Args:
            application_id: Application ID
            tier: 'tier_1', 'tier_2', or 'tier_3'
            total_amount: Total loan amount (₹)
            rate: Annual interest rate (%)
            health: 'poor', 'fair', 'good', or 'excellent'
            
        Returns:
            List of TrancheOutcome (one per tranche)
        """
        outcomes = []
        
        # Tranche plan by tier
        if tier == 'tier_1':
            tranches = [total_amount]
            tenure_months = 12
        elif tier == 'tier_2':
            tranches = [total_amount * 0.6, total_amount * 0.4]
            tenure_months = 24
        elif tier == 'tier_3':
            tranches = [
                total_amount * 0.4,
                total_amount * 0.3,
                total_amount * 0.2,
                total_amount * 0.1
            ]
            tenure_months = 36
        else:
            raise ValueError(f"Unknown tier: {tier}")
        
        # Simulate each tranche
        start_date = datetime(2024, 12, 1)
        
        for tranche_num, tranche_amount in enumerate(tranches, 1):
            # Shift start date for each tranche (assume 60-day gaps)
            tranche_start = start_date + timedelta(days=60 * (tranche_num - 1))
            
            outcome = self.simulate_tranche(
                application_id=application_id,
                tranche_num=tranche_num,
                tranche_amount=tranche_amount,
                annual_rate=rate,
                tenure_months=tenure_months,
                tier=tier,
                health=health,
                start_date=tranche_start
            )
            
            outcomes.append(outcome)
        
        return outcomes


def demo():
    """Demo tranche simulation."""
    print("\n" + "="*70)
    print("DEMO: TRANCHE SIMULATION")
    print("="*70)
    
    simulator = TrancheSimulator(random_seed=42)
    
    # Example 1: Tier 1 loan
    print("\n" + "-"*70)
    print("Example 1: Tier 1 Loan (₹50k, 12 months)")
    print("-"*70)
    
    tier1_outcomes = simulator.simulate_full_loan(
        application_id="app_tier1_001",
        tier='tier_1',
        total_amount=50000,
        rate=18.5,
        health='good'
    )
    
    for outcome in tier1_outcomes:
        print(f"\nTranche {outcome.tranche_num}: ₹{outcome.tranche_amount:,.0f}")
        print(f"  Completed all EMIs: {outcome.completed_all_emis}")
        print(f"  Missed EMIs: {outcome.missed_emi_count}")
        print(f"  Eligible for next: {outcome.eligible_for_next_tranche}")
        
        # Show first 3 EMIs
        for emi in outcome.emi_schedule[:3]:
            print(f"    EMI {emi.emi_num}: {emi.payment_status} ({emi.days_late if emi.days_late else 0} days late)")
    
    # Example 2: Tier 2 loan
    print("\n" + "-"*70)
    print("Example 2: Tier 2 Loan (₹200k, 2 tranches, 24 months)")
    print("-"*70)
    
    tier2_outcomes = simulator.simulate_full_loan(
        application_id="app_tier2_001",
        tier='tier_2',
        total_amount=200000,
        rate=14.0,
        health='fair'
    )
    
    for outcome in tier2_outcomes:
        print(f"\nTranche {outcome.tranche_num}: ₹{outcome.tranche_amount:,.0f}")
        print(f"  Completed all EMIs: {outcome.completed_all_emis}")
        print(f"  Missed EMIs: {outcome.missed_emi_count}")
        print(f"  Eligible for next: {outcome.eligible_for_next_tranche}")
    
    # Example 3: Stop rule triggered
    print("\n" + "-"*70)
    print("Example 3: Stop Rule (2+ missed EMIs freeze tranches)")
    print("-"*70)
    
    tier3_outcomes = simulator.simulate_full_loan(
        application_id="app_tier3_risk",
        tier='tier_3',
        total_amount=500000,
        rate=10.5,
        health='poor'
    )
    
    for outcome in tier3_outcomes:
        print(f"\nTranche {outcome.tranche_num}: ₹{outcome.tranche_amount:,.0f}")
        print(f"  Completed all EMIs: {outcome.completed_all_emis}")
        print(f"  Missed EMIs: {outcome.missed_emi_count}")
        print(f"  Eligible for next: {outcome.eligible_for_next_tranche}")
        
        if outcome.missed_emi_count >= 2:
            print(f"  ⚠️  STOP RULE TRIGGERED: Tranches frozen")
    
    # Aggregate statistics
    print("\n" + "="*70)
    print("STATISTICS")
    print("="*70)
    
    all_outcomes = tier1_outcomes + tier2_outcomes + tier3_outcomes
    
    completed = sum(1 for o in all_outcomes if o.completed_all_emis)
    missed_2_plus = sum(1 for o in all_outcomes if o.missed_emi_count >= 2)
    
    print(f"Total tranches: {len(all_outcomes)}")
    print(f"Completed all EMIs: {completed} ({100*completed/len(all_outcomes):.1f}%)")
    print(f"Frozen (2+ missed): {missed_2_plus} ({100*missed_2_plus/len(all_outcomes):.1f}%)")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    demo()
