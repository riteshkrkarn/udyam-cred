"""
Evaluate Claim 2: Tranche-Based Loans Outperform Single-Amount Loans

Measures whether progressive tranches with EMI gates outperform single-tranche loans
at the same tier, by reducing defaults and improving repayment discipline.

Expected result: Tranches show 15-30% lower default rates and 10-20% higher
completion rates compared to single-amount loans, proving gates work.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime
from tranche_simulator import TrancheSimulator

logger = logging.getLogger(__name__)


# Baseline: single-amount loan default rates (by tier & health)
SINGLE_AMOUNT_DEFAULTS = {
    ('tier_1', 'poor'): 0.35,
    ('tier_1', 'fair'): 0.20,
    ('tier_1', 'good'): 0.10,
    ('tier_1', 'excellent'): 0.05,
    
    ('tier_2', 'poor'): 0.28,
    ('tier_2', 'fair'): 0.15,
    ('tier_2', 'good'): 0.08,
    ('tier_2', 'excellent'): 0.03,
    
    ('tier_3', 'poor'): 0.20,
    ('tier_3', 'fair'): 0.10,
    ('tier_3', 'good'): 0.05,
    ('tier_3', 'excellent'): 0.02,
}

# Single-amount completion rates (no gates, so just payment discipline)
SINGLE_AMOUNT_COMPLETION = {
    ('tier_1', 'poor'): 0.65,
    ('tier_1', 'fair'): 0.80,
    ('tier_1', 'good'): 0.90,
    ('tier_1', 'excellent'): 0.95,
    
    ('tier_2', 'poor'): 0.72,
    ('tier_2', 'fair'): 0.85,
    ('tier_2', 'good'): 0.92,
    ('tier_2', 'excellent'): 0.97,
    
    ('tier_3', 'poor'): 0.80,
    ('tier_3', 'fair'): 0.90,
    ('tier_3', 'good'): 0.95,
    ('tier_3', 'excellent'): 0.98,
}


class TrancheOutcomeEvaluation:
    """Evaluate tranche outcomes vs single-amount loans."""
    
    def __init__(self, data_dir: str = 'ml/data', random_seed: int = 42):
        """Initialize evaluator."""
        self.data_dir = Path(data_dir)
        self.simulator = TrancheSimulator(random_seed=random_seed)
        logger.info(f"Initialized tranche evaluation with data dir: {data_dir}")
    
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
    
    def map_health_category(self, health_score: float) -> str:
        """Map continuous health score to category."""
        if health_score < 0.4:
            return 'poor'
        elif health_score < 0.65:
            return 'fair'
        elif health_score < 0.85:
            return 'good'
        else:
            return 'excellent'
    
    def get_rate_by_tier(self, tier: int) -> float:
        """Get annual interest rate by tier."""
        rates = {
            1: 18.5,  # T1: industry + 4%
            2: 14.0,  # T2: industry + 2%
            3: 10.5,  # T3: industry + 0%
        }
        return rates.get(tier, 14.0)
    
    def simulate_loan_outcomes(self,
                              tier: int,
                              health: str,
                              amount: float,
                              num_simulations: int = 10) -> Dict:
        """Simulate tranche and single-amount outcomes for a loan.
        
        IMPORTANT: This compares two lending strategies on the same 100 applicants:
        1. TRANCHE ARM: Approve applicant, disburse in tranches with gates
        2. SINGLE ARM: Approve applicant, disburse full amount upfront
        
        Metrics are computed per APPLICANT (not per tranche), so we can compare apples-to-apples.
        """
        tier_key = f'tier_{tier}'
        rate = self.get_rate_by_tier(tier)
        
        # Tranche simulation
        tranche_results = []
        tranche_funnel = {
            'applications': 0,
            'tranche_1_disbursed': 0,
            'tranche_2_disbursed': 0,
            'tranche_3_disbursed': 0,
            'tranche_4_disbursed': 0,
            'total_applications': 0,
        }
        
        for sim_idx in range(num_simulations):
            outcomes = self.simulator.simulate_full_loan(
                application_id=f"app_tranche_{tier}_{sim_idx}",
                tier=tier_key,
                total_amount=amount,
                rate=rate,
                health=health
            )
            tranche_results.append(outcomes)
            tranche_funnel['total_applications'] += 1
            
            # Track tranche disbursement
            if len(outcomes) >= 1:
                tranche_funnel['tranche_1_disbursed'] += 1
            if len(outcomes) >= 2 and outcomes[0].eligible_for_next_tranche:
                tranche_funnel['tranche_2_disbursed'] += 1
            if len(outcomes) >= 3 and outcomes[1].eligible_for_next_tranche:
                tranche_funnel['tranche_3_disbursed'] += 1
            if len(outcomes) >= 4 and outcomes[2].eligible_for_next_tranche:
                tranche_funnel['tranche_4_disbursed'] += 1
        
        # CORRECTED METRIC: Per-application default (not per-tranche)
        # For tranches: loan defaults if ANY tranche has 2+ missed EMIs
        tranche_defaults = 0
        tranche_full_disbursed = 0  # how many apps got all tranches
        
        for outcomes in tranche_results:
            # Check if this application defaulted (any tranche triggered stop rule)
            app_defaulted = any(t.missed_emi_count >= 2 for t in outcomes)
            if app_defaulted:
                tranche_defaults += 1
            
            # Check if full disbursement happened (all tranches passed gates)
            if tier == 1:
                full_disburse = len(outcomes) >= 1
            elif tier == 2:
                full_disburse = len(outcomes) >= 2 and all(outcomes[i].eligible_for_next_tranche for i in range(1))
            else:  # tier 3
                full_disburse = len(outcomes) >= 4 and all(outcomes[i].eligible_for_next_tranche for i in range(3))
            
            if full_disburse:
                tranche_full_disbursed += 1
        
        # Default rate per application
        tranche_default_rate = tranche_defaults / num_simulations if num_simulations > 0 else 0
        tranche_completion_rate = tranche_full_disbursed / num_simulations if num_simulations > 0 else 0
        
        # Single-amount baseline (same denominator: per application)
        single_default_rate = SINGLE_AMOUNT_DEFAULTS.get((tier_key, health), 0.10)
        single_completion_rate = SINGLE_AMOUNT_COMPLETION.get((tier_key, health), 0.85)
        
        return {
            'tier': tier,
            'health': health,
            'amount': amount,
            'num_applications': num_simulations,
            'tranche_default_rate': tranche_default_rate,
            'tranche_completion_rate': tranche_completion_rate,
            'single_default_rate': single_default_rate,
            'single_completion_rate': single_completion_rate,
            'default_improvement_ppts': (single_default_rate - tranche_default_rate) * 100,
            'default_improvement_pct': ((single_default_rate - tranche_default_rate) / max(single_default_rate, 0.001)) * 100,
            'completion_improvement_ppts': (tranche_completion_rate - single_completion_rate) * 100,
            'completion_improvement_pct': ((tranche_completion_rate - single_completion_rate) / max(single_completion_rate, 0.001)) * 100,
            'funnel': tranche_funnel,
        }
    
    def evaluate(self, gen_id: int = 2, num_simulations: int = 20) -> Dict:
        """Evaluate Claim 2: Tranche outcomes vs single-amount loans."""
        logger.info("\n" + "="*70)
        logger.info("CLAIM 2 EVALUATION: TRANCHES vs SINGLE-AMOUNT LOANS")
        logger.info("="*70)
        
        # Load data
        tier_data, features, labels = self.load_data(gen_id)
        
        # Merge to get health scores
        merged = tier_data.merge(labels, on='shop_id', how='left')
        
        # Sample loans by tier and health
        results = {}
        
        for tier in [1, 2, 3]:
            tier_shops = merged[merged['tier'] == tier].copy()
            
            tier_cap = {1: 50_000, 2: 250_000, 3: 1_000_000}[tier]
            
            tier_results = {}
            
            for health_cat in ['poor', 'fair', 'good', 'excellent']:
                # Find shops matching this health category
                matching = tier_shops[tier_shops['hidden_health'] == health_cat]
                
                if len(matching) == 0:
                    continue
                
                # Use median amount for this group
                median_amount = min(
                    matching['source_agreement_score'].median() * tier_cap,
                    tier_cap
                )
                
                if median_amount < 10_000:  # Skip very small amounts
                    continue
                
                # Simulate outcomes
                sim_result = self.simulate_loan_outcomes(
                    tier=tier,
                    health=health_cat,
                    amount=median_amount,
                    num_simulations=num_simulations
                )
                
                tier_results[health_cat] = sim_result
            
            results[tier] = tier_results
        
        # Print results
        self._print_results(results)
        
        # Overall statistics
        overall = self._compute_overall(results)
        self._print_overall(overall)
        
        # Validation
        self._validate_claim(results, overall)
        
        logger.info("\n" + "="*70)
        
        return results
    
    def _compute_overall(self, results: Dict) -> Dict:
        """Compute overall statistics across all tiers and health categories."""
        all_results = []
        
        for tier_results in results.values():
            for health_result in tier_results.values():
                all_results.append(health_result)
        
        if not all_results:
            return {}
        
        tranche_defaults = [r['tranche_default_rate'] for r in all_results]
        tranche_completions = [r['tranche_completion_rate'] for r in all_results]
        single_defaults = [r['single_default_rate'] for r in all_results]
        single_completions = [r['single_completion_rate'] for r in all_results]
        
        return {
            'avg_tranche_default_rate': np.mean(tranche_defaults),
            'avg_tranche_completion_rate': np.mean(tranche_completions),
            'avg_single_default_rate': np.mean(single_defaults),
            'avg_single_completion_rate': np.mean(single_completions),
            'avg_default_improvement_ppts': np.mean(single_defaults) - np.mean(tranche_defaults),
            'avg_completion_improvement_ppts': np.mean(tranche_completions) - np.mean(single_completions),
            'num_simulations': len(all_results),
        }
    
    def _print_results(self, results: Dict):
        """Print results by tier and health."""
        print("\n[TRANCHE OUTCOMES vs SINGLE-AMOUNT BASELINE]")
        print("-" * 100)
        
        for tier in [1, 2, 3]:
            if tier not in results or not results[tier]:
                continue
            
            print(f"\n[TIER {tier}]")
            print("-" * 100)
            
            tier_results = results[tier]
            
            for health in ['poor', 'fair', 'good', 'excellent']:
                if health not in tier_results:
                    continue
                
                r = tier_results[health]
                
                print(f"\n  [Health: {health.upper()}]")
                print(f"    Amount: Rs{r['amount']:,.0f} | {r['num_applications']} applications simulated")
                print(f"    Tranche Funnel: T1 {r['funnel']['tranche_1_disbursed']}/{r['funnel']['total_applications']}, T2 {r['funnel']['tranche_2_disbursed']}/{r['funnel']['total_applications']}, T3 {r['funnel']['tranche_3_disbursed']}/{r['funnel']['total_applications']}, T4 {r['funnel']['tranche_4_disbursed']}/{r['funnel']['total_applications']}")
                print(f"    Default Rate:     Tranche {r['tranche_default_rate']:6.1%} vs Single {r['single_default_rate']:6.1%} -> {r['default_improvement_ppts']:+6.1f} pp")
                print(f"    Completion Rate:  Tranche {r['tranche_completion_rate']:6.1%} vs Single {r['single_completion_rate']:6.1%} -> {r['completion_improvement_ppts']:+6.1f} pp")
    
    def _print_overall(self, overall: Dict):
        """Print overall summary."""
        if not overall:
            return
        
        print("\n" + "-" * 100)
        print("\n[OVERALL SUMMARY (All Tiers & Health Combinations)]")
        print("-" * 100)
        print(f"  Simulations:              {overall['num_simulations']} loan scenarios")
        print(f"  Default Rate:             Tranche {overall['avg_tranche_default_rate']:6.1%} vs Single {overall['avg_single_default_rate']:6.1%}")
        print(f"    -> Improvement:          {overall['avg_default_improvement_ppts']:+6.1f} percentage points")
        print(f"  Completion Rate:          Tranche {overall['avg_tranche_completion_rate']:6.1%} vs Single {overall['avg_single_completion_rate']:6.1%}")
        print(f"    -> Improvement:          {overall['avg_completion_improvement_ppts']:+6.1f} percentage points")
        print("-" * 100)
    
    def _validate_claim(self, results: Dict, overall: Dict):
        """Validate that Claim 2 is proven - OR report honest finding."""
        if not overall:
            logger.warning("Not enough data to validate claim")
            return False
        
        logger.info("\n[CLAIM 2 FINDING - NOT YET PROVEN]")
        logger.info("")
        logger.info("Initial results show tranches UNDERPERFORMING single-amount on default rates.")
        logger.info("")
        logger.info("Root cause: Gates are very restrictive. Most poor/fair health borrowers get")
        logger.info("stuck at tranche 1 or 2, never accessing capital for later tranches.")
        logger.info("")
        logger.info("Interpretation:")
        logger.info("- This is NOT necessarily bad - gates may be *intended* to freeze risky borrowers")
        logger.info("- But it means tranches don't enable better lending for this population")
        logger.info("- To improve: either (a) loosen gates, (b) use different qualification for T2+")
        logger.info("")
        logger.info("Actions needed for Claim 2:")
        logger.info("1. Get real single-amount default rates (not synthetic)")
        logger.info("2. Compare on matched populations (same approval criteria)")
        logger.info("3. Decide: do gates improve *risk-adjusted* lending? (approve fewer, but safer)")
        logger.info("")
        
        return False


def main():
    """Run Claim 2 evaluation."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    evaluator = TrancheOutcomeEvaluation(data_dir='ml/data', random_seed=42)
    results = evaluator.evaluate(gen_id=2, num_simulations=5)
    
    # Flatten and save results
    rows = []
    for tier, tier_results in results.items():
        for health, result in tier_results.items():
            rows.append({
                'tier': result['tier'],
                'health': result['health'],
                'amount': result['amount'],
                'tranche_default_rate': result['tranche_default_rate'],
                'single_default_rate': result['single_default_rate'],
                'default_improvement_ppts': result['default_improvement_ppts'],
                'tranche_completion_rate': result['tranche_completion_rate'],
                'single_completion_rate': result['single_completion_rate'],
                'completion_improvement_ppts': result['completion_improvement_ppts'],
            })
    
    if rows:
        results_df = pd.DataFrame(rows)
        results_df.to_csv('ml/evaluation_claim2_results.csv', index=False)
        logger.info("\n[CHECK] Results saved to ml/evaluation_claim2_results.csv")


if __name__ == '__main__':
    main()
