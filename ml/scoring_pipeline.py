"""
End-to-end scoring pipeline: Evidence → Tier → ML Score → Amount → Tranches

This combines tier classification, ML scoring, and amount calculation
into a single decision pipeline.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
import logging
import pandas as pd

from tier_rules import (
    TierClassifier, TierEvidenceInput, AmountCalculator, TrancheEngine, Tier
)
from scorer import load_ensemble

logger = logging.getLogger(__name__)


@dataclass
class ScoringDecision:
    """Complete scoring decision."""
    shop_id: str
    tier: int  # 1, 2, or 3
    tier_name: str
    
    # ML scores
    default_probability: float
    risk_band: str
    scorecard_confidence: float
    safe_emi: float
    
    # Amount
    capacity_amount: float
    tier_cap: float
    stock_limit: float
    final_amount: float
    
    # Tranches
    tranched: bool
    tranche_schedule: Optional[list] = None
    
    # Metadata
    reasons: list = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = {
            'shop_id': self.shop_id,
            'tier': self.tier,
            'tier_name': self.tier_name,
            'default_probability': round(self.default_probability, 4),
            'risk_band': self.risk_band,
            'scorecard_confidence': round(self.scorecard_confidence, 4),
            'safe_emi': round(self.safe_emi, 0),
            'capacity_amount': round(self.capacity_amount, 0),
            'tier_cap': round(self.tier_cap, 0),
            'stock_limit': round(self.stock_limit, 0),
            'final_amount': round(self.final_amount, 0),
            'tranched': self.tranched,
            'reasons': self.reasons or []
        }
        
        if self.tranche_schedule:
            result['tranche_schedule'] = self.tranche_schedule
        
        return result


class ScoringPipeline:
    """End-to-end scoring: evidence → tier → amount → tranches."""
    
    def __init__(self, models_dir: str = 'models'):
        """
        Initialize pipeline with loaded models and rules.
        
        Args:
            models_dir: Path to trained models
        """
        self.ensemble = load_ensemble(models_dir)
        self.tier_classifier = TierClassifier()
        self.amount_calculator = AmountCalculator()
        self.tranche_engine = TrancheEngine()
        
        logger.info("✓ Scoring pipeline initialized")
    
    def score(self,
              shop_id: str,
              features: Dict[str, float],
              evidence: TierEvidenceInput,
              stock_value: float) -> ScoringDecision:
        """
        Score a single shop end-to-end.
        
        Pipeline:
        1. Classify tier based on evidence
        2. Get ML scores (scorecard + capacity)
        3. Calculate amount (min of capacity, tier cap, stock limit)
        4. Generate tranche schedule if Tier 3
        
        Args:
            shop_id: Shop identifier
            features: Dictionary of {feature_name: value} for ML
            evidence: TierEvidenceInput (has_gst, has_udyam, etc.)
            stock_value: Shop's stock value (₹)
            
        Returns:
            ScoringDecision with all scores and amount
        """
        logger.info(f"Scoring shop: {shop_id}")
        
        # Step 1: Classify tier
        tier_assignment = self.tier_classifier.classify(evidence)
        tier = tier_assignment.tier
        tier_reasons = tier_assignment.reasons.copy()
        
        logger.info(f"  Tier: {tier.name}")
        
        # Step 2: Get ML scores
        ml_result = self.ensemble.score_shop(features)
        scorecard = ml_result.scorecard
        capacity = ml_result.capacity
        
        logger.info(f"  Default prob: {scorecard.default_probability:.2%}")
        logger.info(f"  Safe EMI: ₹{capacity.predicted_safe_emi:,.0f}")
        
        # Step 3: Calculate amount
        amount_details = self.amount_calculator.calculate(
            evidence=evidence,
            capacity_model_emi=capacity.predicted_safe_emi,
            stock_limit=stock_value
        )
        
        final_amount = amount_details['final_amount']
        logger.info(f"  Final amount: ₹{final_amount:,.0f}")
        
        # Step 4: Generate tranches if Tier 3
        tranche_schedule = None
        if tier == Tier.TIER_3:
            schedule = self.tranche_engine.calculate_tier3_schedule(final_amount)
            tranche_schedule = [
                {
                    'number': t['number'],
                    'amount': round(t['amount'], 0),
                    'condition': t['condition'],
                    'condition_code': t['condition_code']
                }
                for t in schedule.tranches
            ]
            logger.info(f"  Tranches: 3 (40/30/30)")
        
        # Combine reasons
        all_reasons = tier_reasons + amount_details['reasons']
        
        # Create decision
        decision = ScoringDecision(
            shop_id=shop_id,
            tier=tier.value,
            tier_name=tier.name,
            default_probability=scorecard.default_probability,
            risk_band=scorecard.risk_band,
            scorecard_confidence=scorecard.confidence,
            safe_emi=capacity.predicted_safe_emi,
            capacity_amount=amount_details['capacity_amount'],
            tier_cap=amount_details['tier_cap'],
            stock_limit=amount_details['stock_limit'],
            final_amount=final_amount,
            tranched=amount_details['tranched'],
            tranche_schedule=tranche_schedule,
            reasons=all_reasons
        )
        
        logger.info(f"✓ Scoring complete")
        return decision
    
    def score_batch(self,
                   df: pd.DataFrame,
                   evidence_column: str = 'evidence',
                   stock_column: str = 'stock_value') -> pd.DataFrame:
        """
        Score a batch of shops.
        
        Args:
            df: DataFrame with:
                - shop_id (required)
                - All feature columns
                - evidence_column (optional, defaults to 'evidence')
                - stock_column (defaults to 'stock_value')
            evidence_column: Name of column with TierEvidenceInput dict
            stock_column: Name of column with stock value
            
        Returns:
            DataFrame with scoring results
        """
        results = []
        
        for idx, row in df.iterrows():
            shop_id = row['shop_id']
            
            # Extract features
            feature_names = self.ensemble.get_feature_names()
            features = {
                fname: row.get(fname, 0)
                for fname in feature_names
            }
            
            # Extract evidence
            if evidence_column in row and isinstance(row[evidence_column], TierEvidenceInput):
                evidence = row[evidence_column]
            else:
                # Assume evidence from row data
                evidence = TierEvidenceInput(
                    has_gst_filings=row.get('has_gst_filings', False),
                    has_udyam_registration=row.get('has_udyam_registration', False),
                    has_prior_repayment_record=row.get('has_prior_repayment_record', False),
                    months_bank_history=row.get('months_bank_history', 0)
                )
            
            # Extract stock
            stock_value = row.get(stock_column, 0)
            
            # Score
            decision = self.score(shop_id, features, evidence, stock_value)
            results.append(decision.to_dict())
        
        return pd.DataFrame(results)


def demo_single_shop():
    """Demo: Score a single shop."""
    print("\n" + "="*70)
    print("DEMO: SINGLE SHOP SCORING")
    print("="*70)
    
    # Initialize pipeline
    pipeline = ScoringPipeline('models')
    
    # Example shop
    shop_id = "shop_demo_001"
    
    # Evidence
    evidence = TierEvidenceInput(
        has_gst_filings=True,
        has_udyam_registration=False,
        has_prior_repayment_record=False,
        months_bank_history=18
    )
    
    # Features (simplified, real ones from feature_builder)
    features = {
        'upi_inflow_mean': 120000,
        'upi_inflow_std': 25000,
        'cash_deposits_mean': 50000,
        'cash_withdrawals_mean': 40000,
        'balance_trend': 0.5,
        'gst_turnover_total': 1800000,
        'gst_filing_rate': 0.95,
        'reconciliation_gap_mean': 0.1,
        'stock_value_mean': 75000,
        'stock_turnover_days': 30,
        'purchases_count': 45,
        'suppliers_unique': 12,
        'supplier_confirmation_rate': 0.8,
        'vintage_sources_count': 3,
        'transfers_count': 8,
        'roundtrip_transfers_count': 0,
        'roundtrip_rate': 0.0
    }
    
    stock_value = 75000
    
    # Score
    decision = pipeline.score(shop_id, features, evidence, stock_value)
    
    # Display
    print(f"\nShop ID: {decision.shop_id}")
    print(f"\nTIER: {decision.tier_name} (evidence: GST filings, 18mo bank history)")
    print(f"\nML SCORES:")
    print(f"  Default probability: {decision.default_probability:.2%}")
    print(f"  Risk band: {decision.risk_band}")
    print(f"  Confidence: {decision.scorecard_confidence:.2f}")
    print(f"  Safe EMI: ₹{decision.safe_emi:,.0f}")
    print(f"\nAMOUNT CALCULATION:")
    print(f"  Capacity (from ML): ₹{decision.capacity_amount:,.0f}")
    print(f"  Tier cap (Tier 2): ₹{decision.tier_cap:,.0f}")
    print(f"  Stock limit: ₹{decision.stock_limit:,.0f}")
    print(f"  → Final amount: ₹{decision.final_amount:,.0f}")
    print(f"\nTRANCHES: No (Tier 2 is not tranched)")
    print(f"\nREASONS:")
    for reason in decision.reasons:
        print(f"  • {reason}")
    
    print("\n" + "="*70)


def demo_tier_comparison():
    """Demo: Compare all three tiers."""
    print("\n" + "="*70)
    print("DEMO: TIER COMPARISON")
    print("="*70)
    
    pipeline = ScoringPipeline('models')
    
    # Same features for all three
    features = {
        'upi_inflow_mean': 120000,
        'upi_inflow_std': 25000,
        'cash_deposits_mean': 50000,
        'cash_withdrawals_mean': 40000,
        'balance_trend': 0.5,
        'gst_turnover_total': 1800000,
        'gst_filing_rate': 0.95,
        'reconciliation_gap_mean': 0.1,
        'stock_value_mean': 75000,
        'stock_turnover_days': 30,
        'purchases_count': 45,
        'suppliers_unique': 12,
        'supplier_confirmation_rate': 0.8,
        'vintage_sources_count': 3,
        'transfers_count': 8,
        'roundtrip_transfers_count': 0,
        'roundtrip_rate': 0.0
    }
    stock_value = 75000
    
    # Tier 1: No evidence
    print("\n--- TIER 1: No evidence ---")
    evidence1 = TierEvidenceInput(
        has_gst_filings=False,
        has_udyam_registration=False,
        has_prior_repayment_record=False,
        months_bank_history=12
    )
    decision1 = pipeline.score("shop_tier1", features, evidence1, stock_value)
    print(f"Amount: ₹{decision1.final_amount:,.0f} (cap: ₹50k)")
    print(f"Tranched: {decision1.tranched}")
    
    # Tier 2: GST
    print("\n--- TIER 2: GST + bank history ---")
    evidence2 = TierEvidenceInput(
        has_gst_filings=True,
        has_udyam_registration=False,
        has_prior_repayment_record=False,
        months_bank_history=18
    )
    decision2 = pipeline.score("shop_tier2", features, evidence2, stock_value)
    print(f"Amount: ₹{decision2.final_amount:,.0f} (cap: ₹300k)")
    print(f"Tranched: {decision2.tranched}")
    
    # Tier 3: Udyam + history
    print("\n--- TIER 3: Udyam + repayment record ---")
    evidence3 = TierEvidenceInput(
        has_gst_filings=True,
        has_udyam_registration=True,
        has_prior_repayment_record=True,
        months_bank_history=36
    )
    decision3 = pipeline.score("shop_tier3", features, evidence3, stock_value)
    print(f"Amount: ₹{decision3.final_amount:,.0f} (cap: ₹1M)")
    print(f"Tranched: {decision3.tranched}")
    if decision3.tranche_schedule:
        for t in decision3.tranche_schedule:
            print(f"  Tranche {t['number']}: ₹{t['amount']:,.0f} ({t['condition']})")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    demo_single_shop()
    demo_tier_comparison()
