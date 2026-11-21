"""
Tier classification and amount rules for UdyamCred.

Tiers depend on evidence (documents) available. Amount rules depend on tier.

Tier 1: No GST / Udyam → money-side only → smallest cap
Tier 2: GST filings or long bank history → scaled by verified window
Tier 3: Udyam + prior repayment record → tranched, highest cap
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Tier(Enum):
    """Product tier based on evidence."""
    TIER_1 = 1  # Money-side only
    TIER_2 = 2  # GST or long bank history
    TIER_3 = 3  # Udyam + repayment history


@dataclass
class TierEvidenceInput:
    """Evidence available for tier classification."""
    has_gst_filings: bool  # 3+ GSTR-1 or GSTR-2B returns
    has_udyam_registration: bool
    has_prior_repayment_record: bool
    months_bank_history: int  # Months of verified bank history


@dataclass
class TierAssignment:
    """Result of tier classification."""
    tier: Tier
    reasons: list  # Why this tier


@dataclass
class AmountRules:
    """Amount caps and rules for a tier."""
    tier: Tier
    min_amount: float  # ₹
    max_amount: float  # ₹
    tranched: bool  # If False, single disbursement


class TierClassifier:
    """Classify shops into tiers based on evidence."""
    
    # Tier decision rules
    TIER_1_MAX_AMOUNT = 50000  # Smallest tier, strictly capped
    TIER_2_MIN_AMOUNT = 75000
    TIER_2_MAX_AMOUNT = 300000
    TIER_3_MIN_AMOUNT = 200000
    TIER_3_MAX_AMOUNT = 1000000
    
    # Evidence thresholds
    GST_FILING_THRESHOLD = 3  # Minimum GST returns
    BANK_HISTORY_THRESHOLD = 24  # Months for Tier 2
    
    def classify(self, evidence: TierEvidenceInput) -> TierAssignment:
        """
        Classify a shop into a tier.
        
        Decision tree:
        1. If Udyam + prior repayment → Tier 3
        2. Else if GST ≥ 3 filings or bank ≥ 24 months → Tier 2
        3. Else → Tier 1
        
        Args:
            evidence: TierEvidenceInput with documents available
            
        Returns:
            TierAssignment with tier and reasons
        """
        reasons = []
        
        # Rule 1: Tier 3 (highest evidence)
        if evidence.has_udyam_registration and evidence.has_prior_repayment_record:
            reasons.append("Udyam registration confirmed")
            reasons.append("Prior repayment record with lender")
            return TierAssignment(
                tier=Tier.TIER_3,
                reasons=reasons
            )
        
        # Rule 2: Tier 2 (medium evidence)
        if evidence.has_gst_filings or evidence.months_bank_history >= self.BANK_HISTORY_THRESHOLD:
            if evidence.has_gst_filings:
                reasons.append("GST filings available")
            if evidence.months_bank_history >= self.BANK_HISTORY_THRESHOLD:
                reasons.append(f"Bank history: {evidence.months_bank_history} months")
            
            return TierAssignment(
                tier=Tier.TIER_2,
                reasons=reasons
            )
        
        # Rule 3: Tier 1 (minimum evidence)
        reasons.append("Below GST limit or insufficient bank history")
        reasons.append("Money-side only (UPI, bank, ledger)")
        return TierAssignment(
            tier=Tier.TIER_1,
            reasons=reasons
        )
    
    def get_amount_rules(self, tier: Tier) -> AmountRules:
        """
        Get amount cap and disbursement rules for a tier.
        
        Args:
            tier: Product tier
            
        Returns:
            AmountRules with caps and tranche info
        """
        if tier == Tier.TIER_1:
            return AmountRules(
                tier=Tier.TIER_1,
                min_amount=10000,
                max_amount=self.TIER_1_MAX_AMOUNT,
                tranched=False
            )
        
        elif tier == Tier.TIER_2:
            return AmountRules(
                tier=Tier.TIER_2,
                min_amount=self.TIER_2_MIN_AMOUNT,
                max_amount=self.TIER_2_MAX_AMOUNT,
                tranched=False
            )
        
        elif tier == Tier.TIER_3:
            return AmountRules(
                tier=Tier.TIER_3,
                min_amount=self.TIER_3_MIN_AMOUNT,
                max_amount=self.TIER_3_MAX_AMOUNT,
                tranched=True
            )
        
        else:
            raise ValueError(f"Unknown tier: {tier}")


class AmountCalculator:
    """Calculate loan amount based on ML models and tier rules."""
    
    def __init__(self):
        self.classifier = TierClassifier()
    
    def calculate(self, 
                  evidence: TierEvidenceInput,
                  capacity_model_emi: float,
                  stock_limit: float,
                  family_size: int = 1) -> Dict:
        """
        Calculate final loan amount for a shop.
        
        Final amount = min(capacity_model, tier_cap, stock_limit)
        
        Then apply household budget adjustment if needed.
        
        Args:
            evidence: TierEvidenceInput
            capacity_model_emi: Safe EMI from ML model (₹/month)
            stock_limit: Stock-based limit (₹)
            family_size: For EMI household adjustment
            
        Returns:
            Dict with:
            - tier
            - capacity_amount (from ML model)
            - tier_cap
            - stock_limit
            - final_amount
            - tranched
            - reasons
        """
        # Classify tier
        tier_assignment = self.classifier.classify(evidence)
        tier = tier_assignment.tier
        
        # Get amount rules
        amount_rules = self.classifier.get_amount_rules(tier)
        
        # Convert EMI to amount (simple: EMI * 24 months as rough proxy)
        # In reality, would use actual loan term and interest rate
        capacity_amount = capacity_model_emi * 24
        
        # Apply tier cap
        tier_cap = amount_rules.max_amount
        
        # Final amount is minimum of three constraints
        final_amount = min(capacity_amount, tier_cap, stock_limit)
        
        # Ensure within tier bounds
        final_amount = max(final_amount, amount_rules.min_amount)
        final_amount = min(final_amount, amount_rules.max_amount)
        
        return {
            'tier': tier.value,
            'tier_name': tier.name,
            'capacity_amount': round(capacity_amount, 0),
            'tier_cap': tier_cap,
            'stock_limit': stock_limit,
            'final_amount': round(final_amount, 0),
            'tranched': amount_rules.tranched,
            'reasons': tier_assignment.reasons + [
                f"Capacity model: ₹{capacity_amount:,.0f}",
                f"Tier cap: ₹{tier_cap:,.0f}",
                f"Stock limit: ₹{stock_limit:,.0f}"
            ]
        }


# ===== Tranche Rules =====

@dataclass
class TrancheSchedule:
    """Tranche disbursement schedule."""
    tier: Tier
    total_amount: float
    tranches: list  # List of {amount, condition}


class TrancheEngine:
    """Manage tranche release and stop conditions."""
    
    def __init__(self):
        pass
    
    def calculate_tier3_schedule(self, total_amount: float) -> TrancheSchedule:
        """
        Calculate tranche schedule for Tier 3 (3 tranches).
        
        Tier 3: 40% initial, 30% after 2 EMIs on time, 30% after 4 EMIs on time.
        
        Args:
            total_amount: Total loan amount
            
        Returns:
            TrancheSchedule with disbursement plan
        """
        t1 = round(total_amount * 0.40, 0)
        t2 = round(total_amount * 0.30, 0)
        t3 = round(total_amount * 0.30, 0)
        
        return TrancheSchedule(
            tier=Tier.TIER_3,
            total_amount=total_amount,
            tranches=[
                {
                    'number': 1,
                    'amount': t1,
                    'condition': 'Initial disbursement',
                    'condition_code': 'INITIAL'
                },
                {
                    'number': 2,
                    'amount': t2,
                    'condition': '2 EMIs paid on time (no missed payments)',
                    'condition_code': 'EMI_2_SUCCESS'
                },
                {
                    'number': 3,
                    'amount': t3,
                    'condition': '4 EMIs paid on time (no missed payments)',
                    'condition_code': 'EMI_4_SUCCESS'
                }
            ]
        )
    
    def should_freeze_tranches(self, missed_emi_count: int) -> bool:
        """
        Check if further tranches should be frozen.
        
        Rule: 2 missed EMIs → freeze further tranches.
        
        Args:
            missed_emi_count: Number of missed EMIs so far
            
        Returns:
            True if tranches should be frozen
        """
        return missed_emi_count >= 2
    
    def get_next_tranche(self, schedule: TrancheSchedule, 
                        emi_paid: int, missed_emi: int) -> Optional[Dict]:
        """
        Determine next tranche to release.
        
        Args:
            schedule: TrancheSchedule for this loan
            emi_paid: Number of EMIs paid successfully
            missed_emi: Number of missed EMIs
            
        Returns:
            Next tranche dict, or None if all released or frozen
        """
        # Check if frozen
        if self.should_freeze_tranches(missed_emi):
            logger.info(f"Tranches frozen: {missed_emi} missed EMIs")
            return None
        
        # Find next unreleased tranche
        for tranche in schedule.tranches:
            tranche_num = tranche['number']
            
            if tranche_num == 1:
                # Already disbursed
                continue
            elif tranche_num == 2 and emi_paid >= 2:
                return tranche
            elif tranche_num == 3 and emi_paid >= 4:
                return tranche
        
        return None


def demo():
    """Demo tier classification and amount calculation."""
    classifier = TierClassifier()
    calculator = AmountCalculator()
    
    # Example 1: Tier 1 (no documents)
    print("\n" + "="*60)
    print("EXAMPLE 1: Tier 1 (Money-side only)")
    print("="*60)
    
    evidence1 = TierEvidenceInput(
        has_gst_filings=False,
        has_udyam_registration=False,
        has_prior_repayment_record=False,
        months_bank_history=12
    )
    tier1 = classifier.classify(evidence1)
    print(f"Tier: {tier1.tier.name}")
    print(f"Reasons: {', '.join(tier1.reasons)}")
    
    amount1 = calculator.calculate(
        evidence1,
        capacity_model_emi=8000,
        stock_limit=100000
    )
    print(f"Loan amount: ₹{amount1['final_amount']:,.0f} (cap: ₹{amount1['tier_cap']:,.0f})")
    
    # Example 2: Tier 2 (GST filings)
    print("\n" + "="*60)
    print("EXAMPLE 2: Tier 2 (GST filings)")
    print("="*60)
    
    evidence2 = TierEvidenceInput(
        has_gst_filings=True,
        has_udyam_registration=False,
        has_prior_repayment_record=False,
        months_bank_history=18
    )
    tier2 = classifier.classify(evidence2)
    print(f"Tier: {tier2.tier.name}")
    print(f"Reasons: {', '.join(tier2.reasons)}")
    
    amount2 = calculator.calculate(
        evidence2,
        capacity_model_emi=15000,
        stock_limit=500000
    )
    print(f"Loan amount: ₹{amount2['final_amount']:,.0f} (cap: ₹{amount2['tier_cap']:,.0f})")
    
    # Example 3: Tier 3 (Udyam + history)
    print("\n" + "="*60)
    print("EXAMPLE 3: Tier 3 (Udyam + repayment history)")
    print("="*60)
    
    evidence3 = TierEvidenceInput(
        has_gst_filings=True,
        has_udyam_registration=True,
        has_prior_repayment_record=True,
        months_bank_history=36
    )
    tier3 = classifier.classify(evidence3)
    print(f"Tier: {tier3.tier.name}")
    print(f"Reasons: {', '.join(tier3.reasons)}")
    
    amount3 = calculator.calculate(
        evidence3,
        capacity_model_emi=20000,
        stock_limit=800000
    )
    print(f"Loan amount: ₹{amount3['final_amount']:,.0f} (cap: ₹{amount3['tier_cap']:,.0f})")
    print(f"Tranched: {amount3['tranched']}")
    
    # Demo tranche schedule
    print("\n" + "="*60)
    print("TRANCHE SCHEDULE (Tier 3)")
    print("="*60)
    
    tranche_engine = TrancheEngine()
    schedule = tranche_engine.calculate_tier3_schedule(amount3['final_amount'])
    
    for t in schedule.tranches:
        print(f"Tranche {t['number']}: ₹{t['amount']:,.0f} ({t['condition']})")


if __name__ == '__main__':
    demo()
