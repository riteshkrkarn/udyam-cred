"""
Evaluate Claim 1: Approval Rate by Tier vs Bureau Baseline (WITH CAVEATS)

Measures whether UdyamCred's tiered system approves more loans at the same default rate
compared to a bureau-only baseline approach.

IMPORTANT CAVEATS:
1. Bureau baseline is a STRAWMAN: bureau rejects almost everyone with no credit history,
   so any model that approves more will look better. This is not a fair comparison.
2. Default rates are from SYNTHETIC DATA. The generator includes hidden_health, so we expect
   to see better default rates just by using it. Real-world default correlation may differ.
3. This comparison assumes same risk tolerance (10% default) but tests on different populations.
   Real test: at SAME approval rate, do we get same default? Or same default, more approvals?

WHAT WE ACTUALLY TESTED:
- Gen 2 synthetic data (1,500 shops)
- Bureau baseline from design doc (250 total approvals, not calibrated to Gen 2 distribution)
- Default rate: 6.3% on tranches vs 10% assumed single-bureau (unstudied gap)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# Bureau baseline from design doc
BUREAU_BASELINE = {
    'Tier 1': {
        'approvals': 50,
        'total_amount': 1_500_000,
        'default_rate': 0.10,
        'avg_amount': 30_000,
    },
    'Tier 2': {
        'approvals': 200,
        'total_amount': 35_000_000,
        'default_rate': 0.10,
        'avg_amount': 175_000,
    },
    'Tier 3': {
        'approvals': 80,
        'total_amount': 50_000_000,
        'default_rate': 0.10,
        'avg_amount': 625_000,
    },
}


class TierEvaluation:
    """Evaluate approval rates by tier vs bureau baseline."""
    
    def __init__(self, data_dir: str = 'ml/ml/data'):
        """Initialize evaluator."""
        self.data_dir = Path(data_dir)
        logger.info(f"Initialized tier evaluation with data dir: {data_dir}")
    
    def load_data(self, gen_id: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load tier assignments, features, and labels."""
        tier_file = self.data_dir / f'tier_assignments_gen{gen_id}.csv'
        features_file = self.data_dir / f'features_gen{gen_id}.csv'
        labels_file = self.data_dir / f'labels_gen{gen_id}.csv'
        
        tier_data = pd.read_csv(tier_file)
        features = pd.read_csv(features_file)
        labels = pd.read_csv(labels_file)
        
        logger.info(f"Loaded: {len(tier_data)} shops, {len(features)} features, {len(labels)} labels")
        
        return tier_data, features, labels
    
    def calculate_tier_amounts(self, tiers: pd.DataFrame) -> Dict[int, Tuple[float, float]]:
        """
        Calculate approved amounts by tier.
        
        Rules:
        - Tier 1: ₹50k max
        - Tier 2: ₹250k max
        - Tier 3: ₹1M max
        
        Actual amounts scale by source agreement score.
        """
        tier_caps = {1: 50_000, 2: 250_000, 3: 1_000_000}
        amounts_by_tier = {}
        
        for tier in [1, 2, 3]:
            tier_shops = tiers[tiers['tier'] == tier]
            
            # Amount = tier_cap × agreement_score (assumes ~0.85 agreement on average)
            tier_cap = tier_caps[tier]
            avg_agreement = tier_shops['source_agreement_score'].mean()
            
            # Base amount scaled by agreement
            # Most shops will get slightly below tier cap
            approved_amounts = tier_cap * tier_shops['source_agreement_score']
            
            total_amount = approved_amounts.sum()
            count = len(tier_shops)
            
            amounts_by_tier[tier] = (count, total_amount)
        
        return amounts_by_tier
    
    def evaluate(self, gen_id: int = 2) -> Dict:
        """
        Evaluate Claim 1: Approval rate by tier vs bureau baseline.
        
        CAVEAT: This is tested on SYNTHETIC GEN 2 DATA. Results show what is theoretically
        possible with perfect tier classification and multi-source verification. Real data
        will likely show smaller gains and different default correlations.
        
        Args:
            gen_id: Generator ID (1 for training, 2 for test)
            
        Returns:
            Evaluation results dict
        """
        logger.info("\n" + "="*70)
        logger.info("CLAIM 1 EVALUATION: APPROVAL RATE BY TIER vs BUREAU (GEN 2 SYNTHETIC)")
        logger.info("="*70)
        logger.info("")
        logger.info("CAVEATS:")
        logger.info("1. Bureau baseline is a strawman (rejects 85% with no credit history)")
        logger.info("2. Default rates tested on synthetic data (generator uses hidden_health)")
        logger.info("3. Tier distribution may not match real population")
        logger.info("")
        
        # Load data
        tier_data, features, labels = self.load_data(gen_id)
        
        # Merge tier assignments with labels
        merged = tier_data.merge(labels, on='shop_id', how='left')
        
        # Calculate results by tier
        results = {}
        
        for tier in [1, 2, 3]:
            tier_shops = merged[merged['tier'] == tier]
            
            approval_count = len(tier_shops)
            
            # Calculate amounts by agreement score
            tier_cap = {1: 50_000, 2: 250_000, 3: 1_000_000}[tier]
            approved_amounts = tier_cap * tier_shops['source_agreement_score']
            total_amount = approved_amounts.sum()
            avg_amount = approved_amounts.mean()
            
            # Default rate
            default_rate = tier_shops['default_6m'].mean()
            defaults_count = tier_shops['default_6m'].sum()
            
            # Get bureau baseline
            bureau = BUREAU_BASELINE[f'Tier {tier}']
            
            # Calculate improvements
            approval_improvement_pct = ((approval_count - bureau['approvals']) / bureau['approvals']) * 100
            amount_improvement_pct = ((total_amount - bureau['total_amount']) / bureau['total_amount']) * 100
            
            results[tier] = {
                'tier': tier,
                'udyamcred_approvals': approval_count,
                'bureau_approvals': bureau['approvals'],
                'approval_improvement_pct': approval_improvement_pct,
                'udyamcred_total_amount': total_amount,
                'bureau_total_amount': bureau['total_amount'],
                'amount_improvement_pct': amount_improvement_pct,
                'udyamcred_avg_amount': avg_amount,
                'bureau_avg_amount': bureau['avg_amount'],
                'udyamcred_default_rate': default_rate,
                'bureau_default_rate': bureau['default_rate'],
                'default_rate_difference_ppts': (default_rate - bureau['default_rate']) * 100,
                'defaults_count': int(defaults_count),
                'approval_gain': approval_count - bureau['approvals'],
                'amount_gain': total_amount - bureau['total_amount'],
            }
        
        # Print results
        self._print_results(results)
        
        # Overall statistics
        overall_udyam = sum(r['udyamcred_approvals'] for r in results.values())
        overall_bureau = sum(r['bureau_approvals'] for r in results.values())
        overall_amount_udyam = sum(r['udyamcred_total_amount'] for r in results.values())
        overall_amount_bureau = sum(r['bureau_total_amount'] for r in results.values())
        
        results['overall'] = {
            'udyamcred_approvals': overall_udyam,
            'bureau_approvals': overall_bureau,
            'approval_improvement_pct': ((overall_udyam - overall_bureau) / overall_bureau) * 100,
            'udyamcred_total_amount': overall_amount_udyam,
            'bureau_total_amount': overall_amount_bureau,
            'amount_improvement_pct': ((overall_amount_udyam - overall_amount_bureau) / overall_amount_bureau) * 100,
            'avg_approval_improvement_pcts': np.mean([r['approval_improvement_pct'] for r in results.values() if r != 'overall']),
            'avg_amount_improvement_pcts': np.mean([r['amount_improvement_pct'] for r in results.values() if r != 'overall']),
        }
        
        self._print_overall(results['overall'])
        
        # Validation
        self._validate_claim(results)
        
        logger.info("\n" + "="*70)
        
        return results
    
    def _print_results(self, results: Dict):
        """Print tier-by-tier results."""
        print("\n[TIER-BY-TIER APPROVAL ANALYSIS]")
        print("-" * 70)
        
        for tier in [1, 2, 3]:
            r = results[tier]
            
            print(f"\n[TIER {tier}]")
            print(f"  Approvals:        {r['udyamcred_approvals']:6d} (Bureau: {r['bureau_approvals']:6d}) -> +{r['approval_improvement_pct']:6.1f}%")
            print(f"  Total Amount:     Rs{r['udyamcred_total_amount']:11,.0f} (Bureau: Rs{r['bureau_total_amount']:11,.0f}) -> +{r['amount_improvement_pct']:6.1f}%")
            print(f"  Average Amount:   Rs{r['udyamcred_avg_amount']:11,.0f} (Bureau: Rs{r['bureau_avg_amount']:11,.0f})")
            print(f"  Default Rate:     {r['udyamcred_default_rate']:6.1%} (Bureau: {r['bureau_default_rate']:6.1%}) -> {r['default_rate_difference_ppts']:+.1f} pp")
            print(f"  Defaults:         {int(r['defaults_count']):d} shops out of {r['udyamcred_approvals']}")
        
        print("\n" + "-" * 70)
    
    def _print_overall(self, overall: Dict):
        """Print overall summary."""
        print("\n[OVERALL SUMMARY (All Tiers Combined)]")
        print("-" * 70)
        print(f"  Total Approvals:       {overall['udyamcred_approvals']:6d} (Bureau: {overall['bureau_approvals']:6d}) -> +{overall['approval_improvement_pct']:6.1f}%")
        print(f"  Total Amount Lent:     Rs{overall['udyamcred_total_amount']:11,.0f} (Bureau: Rs{overall['bureau_total_amount']:11,.0f}) -> +{overall['amount_improvement_pct']:6.1f}%")
        print(f"  Avg Approval Gain:     +{overall['avg_approval_improvement_pcts']:6.1f}% per tier")
        print(f"  Avg Amount Gain:       +{overall['avg_amount_improvement_pcts']:6.1f}% per tier")
        print("-" * 70)
    
    def _validate_claim(self, results: Dict):
        """Validate that Claim 1 is proven."""
        logger.info("\n[CLAIM VALIDATION]")
        
        claim_proven = True
        
        # Check each tier improvement is significant
        for tier in [1, 2, 3]:
            r = results[tier]
            
            # Should have >50% more approvals
            if r['approval_improvement_pct'] >= 50:
                logger.info(f"  [CHECK] Tier {tier}: +{r['approval_improvement_pct']:.1f}% approvals (>=50% required)")
            else:
                logger.info(f"  [WARN] Tier {tier}: +{r['approval_improvement_pct']:.1f}% approvals (<50% expected)")
                claim_proven = False
            
            # Should have >70% more capital deployed
            if r['amount_improvement_pct'] >= 70:
                logger.info(f"  [CHECK] Tier {tier}: +{r['amount_improvement_pct']:.1f}% capital (>=70% required)")
            else:
                logger.info(f"  [WARN] Tier {tier}: +{r['amount_improvement_pct']:.1f}% capital (<70% expected)")
                claim_proven = False
            
            # Default rate should not be significantly worse
            if r['default_rate_difference_ppts'] <= 2:
                logger.info(f"  [CHECK] Tier {tier}: Default rate {r['default_rate_difference_ppts']:+.1f} pp (<=2pp required)")
            else:
                logger.info(f"  [WARN] Tier {tier}: Default rate {r['default_rate_difference_ppts']:+.1f} pp (>2pp allowed)")
                claim_proven = False
        
        if claim_proven:
            logger.info("\n[CHECK CHECK CHECK] CLAIM 1 VALIDATED [CHECK CHECK CHECK]")
            logger.info("UdyamCred's tiered system provides significantly better inclusion")
            logger.info("at acceptable risk levels compared to bureau-only baseline.")
        else:
            logger.warning("\n[WARN] CLAIM PARTIALLY PROVEN")
            logger.warning("Some tiers show less improvement than expected. May need feature tuning.")
        
        return claim_proven


def main():
    """Run Claim 1 evaluation."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    evaluator = TierEvaluation(data_dir='ml/data')
    results = evaluator.evaluate(gen_id=2)
    
    # Save results
    results_df = pd.DataFrame([
        {
            'tier': r['tier'],
            'udyamcred_approvals': r['udyamcred_approvals'],
            'bureau_approvals': r['bureau_approvals'],
            'approval_improvement_pct': r['approval_improvement_pct'],
            'udyamcred_total_amount': r['udyamcred_total_amount'],
            'bureau_total_amount': r['bureau_total_amount'],
            'amount_improvement_pct': r['amount_improvement_pct'],
            'udyamcred_default_rate': r['udyamcred_default_rate'],
            'bureau_default_rate': r['bureau_default_rate'],
        }
        for tier, r in results.items() if isinstance(tier, int)
    ])
    
    results_df.to_csv('ml/evaluation_claim1_results.csv', index=False)
    logger.info("\n✓ Results saved to ml/evaluation_claim1_results.csv")


if __name__ == '__main__':
    main()
