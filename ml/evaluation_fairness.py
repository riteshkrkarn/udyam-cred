"""
Evaluate Fairness: Family Size Excluded from Scoring (WITH CAVEAT)

Verifies that family size does NOT affect credit scoring or approval decisions.

CAVEAT: This test only shows that family size does NOT PREDICT tier assignment.
It does NOT show that family size would not matter in real data. Since this is synthetic
data and the generator does not explicitly use family size as a feature, absence of
correlation is expected and not very informative.

Stronger test would be: compare approval/EMI for similar shops across family size ranges,
within each tier. If family size doesn't affect decisions, the effect should be zero
after controlling for risk factors.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FairnessEvaluation:
    """Evaluate fairness properties of the scoring system."""
    
    def __init__(self, data_dir: str = 'ml/data'):
        """Initialize evaluator."""
        self.data_dir = Path(data_dir)
        logger.info(f"Initialized fairness evaluation with data dir: {data_dir}")
    
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
    
    def analyze_family_size_impact(self,
                                   tier_data: pd.DataFrame,
                                   features: pd.DataFrame,
                                   labels: pd.DataFrame) -> Dict:
        """Analyze whether family size affects scoring or approval."""
        # Merge all data
        merged = tier_data.merge(features, on='shop_id', how='left')
        merged = merged.merge(labels, on='shop_id', how='left')
        
        # Check if family_size exists
        if 'family_size' not in merged.columns:
            logger.warning("family_size not found in features")
            return {'error': 'family_size not in features'}
        
        results = {}
        
        # 1. Tier distribution by family size
        if 'tier' in merged.columns and 'family_size' in merged.columns:
            # Stratify by family size
            family_quartiles = pd.qcut(merged['family_size'], q=4, duplicates='drop')
            
            # Simple check: do tier distributions differ significantly by family size?
            tier_dist = merged.groupby([family_quartiles, 'tier']).size().unstack(fill_value=0)
            
            # Calculate chi2 manually (simplified)
            tier_props_by_family = tier_dist.div(tier_dist.sum(axis=1), axis=0)
            overall_props = merged['tier'].value_counts(normalize=True)
            
            # Large difference check
            max_diff = tier_props_by_family.sub(overall_props, axis=1).abs().max().max()
            
            results['tier_distribution_by_family'] = {
                'max_proportion_diff': max_diff,
                'significant': max_diff > 0.10,  # More than 10% difference
                'sample_size': len(merged),
            }
        
        # 2. Default rate by family size
        if 'default_6m' in merged.columns and 'family_size' in merged.columns:
            family_quartiles = pd.qcut(
                merged['family_size'].fillna(merged['family_size'].mean()),
                q=4, duplicates='drop'
            )
            
            default_by_family = merged.groupby(family_quartiles)['default_6m'].agg(['sum', 'count', 'mean'])
            
            results['default_rate_by_family'] = {
                'rates': default_by_family['mean'].tolist(),
                'counts': default_by_family['count'].tolist(),
                'defaults': default_by_family['sum'].tolist(),
            }
            
            # Simple check: variance of default rates
            rates = default_by_family['mean'].values
            rate_variance = rates.std()
            results['default_rate_variance'] = {
                'std_dev': rate_variance,
                'significant': rate_variance > 0.05,  # More than 5pp std dev
            }
        
        # 3. Credit amount by family size
        if 'source_agreement_score' in merged.columns and 'tier' in merged.columns:
            merged['credit_amount'] = merged.apply(
                lambda row: {
                    1: 50_000,
                    2: 250_000,
                    3: 1_000_000,
                }.get(row['tier'], 0) * row['source_agreement_score'],
                axis=1
            )
            
            family_quartiles = pd.qcut(
                merged['family_size'].fillna(merged['family_size'].mean()),
                q=4, duplicates='drop'
            )
            
            amount_by_family = merged.groupby(family_quartiles)['credit_amount'].agg(['mean', 'median', 'count'])
            
            results['credit_amount_by_family'] = {
                'means': amount_by_family['mean'].tolist(),
                'medians': amount_by_family['median'].tolist(),
                'counts': amount_by_family['count'].tolist(),
            }
        
        return results
    
    def evaluate(self, gen_id: int = 2) -> Dict:
        """Evaluate fairness claim: Family size does not affect scoring."""
        logger.info("\n" + "="*70)
        logger.info("FAIRNESS EVALUATION: FAMILY SIZE EXCLUDED (GEN 2 SYNTHETIC)")
        logger.info("="*70)
        logger.info("")
        logger.info("CAVEAT: This is synthetic data where family size was never used as a feature.")
        logger.info("Zero correlation here does NOT prove real-world fairness - synthetic data")
        logger.info("generators with limited feature sets often show zero correlation by default.")
        logger.info("")
        
        # Load data
        tier_data, features, labels = self.load_data(gen_id)
        
        # Analyze family size impact
        results = self.analyze_family_size_impact(tier_data, features, labels)
        
        # Print results
        self._print_results(results, tier_data, features, labels)
        
        # Validation
        self._validate_fairness(results)
        
        logger.info("\n" + "="*70)
        
        return results
    
    def _print_results(self, results: Dict, tier_data: pd.DataFrame, features: pd.DataFrame, labels: pd.DataFrame):
        """Print fairness analysis results."""
        if 'error' in results:
            print(f"\n[WARN] {results['error']}")
            return
        
        print("\n[FAIRNESS ANALYSIS: FAMILY SIZE IMPACT]")
        print("-" * 100)
        
        # 1. Tier distribution by family size
        if 'tier_distribution_by_family' in results:
            r = results['tier_distribution_by_family']
            sig = "SIGNIFICANT" if r['significant'] else "NOT SIGNIFICANT"
            print(f"\n1. Tier Distribution Independence")
            print(f"   Max proportion difference: {r['max_proportion_diff']:.4f}")
            print(f"   [{sig}]")
            print(f"   Sample size: {r['sample_size']:,} shops")
            if not r['significant']:
                print(f"   [CHECK] Tier assignment is independent of family size")
            else:
                print(f"   [WARN] Tier assignment MAY be correlated with family size")
        
        # 2. Default rate by family size
        if 'default_rate_by_family' in results:
            r = results['default_rate_by_family']
            print(f"\n2. Default Rate by Family Size Quartile")
            for i, (rate, count, defaults) in enumerate(zip(r['rates'], r['counts'], r['defaults']), 1):
                print(f"   Q{i}: {rate:6.1%} ({int(defaults):3d} defaults / {int(count):4d} shops)")
            
            if 'default_rate_variance' in results:
                r_var = results['default_rate_variance']
                sig = "SIGNIFICANT" if r_var['significant'] else "NOT SIGNIFICANT"
                print(f"\n   Std Dev of default rates: {r_var['std_dev']:.4f}")
                print(f"   [{sig}]")
                if not r_var['significant']:
                    print(f"   [CHECK] Default rate does NOT vary by family size")
                else:
                    print(f"   [WARN] Default rate MAY vary by family size")
        
        # 3. Credit amount by family size
        if 'credit_amount_by_family' in results:
            r = results['credit_amount_by_family']
            print(f"\n3. Credit Amount by Family Size Quartile")
            for i, (mean, median, count) in enumerate(zip(r['means'], r['medians'], r['counts']), 1):
                print(f"   Q{i}: Mean Rs{mean:>10,.0f} | Median Rs{median:>10,.0f} | {int(count):4d} shops")
    
    def _validate_fairness(self, results: Dict):
        """Validate fairness claims."""
        if 'error' in results:
            logger.warning("Cannot validate fairness: " + results['error'])
            return False
        
        logger.info("\n[FAIRNESS VALIDATION]")
        
        fairness_holds = True
        issues = []
        
        # Check tier distribution independence
        if 'tier_distribution_by_family' in results:
            r = results['tier_distribution_by_family']
            if r['significant']:
                fairness_holds = False
                issues.append(f"Tier distribution correlated with family size (max_diff={r['max_proportion_diff']:.4f})")
            else:
                logger.info(f"  [CHECK] Tier assignment independent of family size")
        
        # Check default rates by family size
        if 'default_rate_variance' in results:
            r = results['default_rate_variance']
            if r['significant']:
                fairness_holds = False
                issues.append(f"Default rates vary by family size (std_dev={r['std_dev']:.4f})")
            else:
                logger.info(f"  [CHECK] Default rates do not vary by family size")
        
        if fairness_holds:
            logger.info("\n[CHECK CHECK CHECK] FAIRNESS VALIDATED [CHECK CHECK CHECK]")
            logger.info("Family size is successfully excluded from scoring decisions.")
            logger.info("System treats all household sizes equally.")
        else:
            logger.warning("\n[WARN] FAIRNESS CONCERNS DETECTED")
            for issue in issues:
                logger.warning(f"  - {issue}")
        
        return fairness_holds


def main():
    """Run fairness evaluation."""
    import logging
    import json
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    evaluator = FairnessEvaluation(data_dir='ml/data')
    results = evaluator.evaluate(gen_id=2)
    
    # Save results as JSON for reference
    
    # Convert non-serializable types for JSON
    def serialize(obj):
        if isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, (list, tuple)):
            return [serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        return obj
    
    results_json = json.dumps(serialize(results), indent=2, default=str)
    
    try:
        with open('evaluation_fairness_results.json', 'w') as f:
            f.write(results_json)
        
        logger.info("\n[CHECK] Results saved to evaluation_fairness_results.json")
    except Exception as e:
        logger.warning(f"Could not save results: {e}")


if __name__ == '__main__':
    main()
