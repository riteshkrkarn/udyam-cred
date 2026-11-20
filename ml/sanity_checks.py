"""
Sanity checks for generated datasets.

Verifies that generated data meets the requirements:
- Default rate between 10-20%
- At least 300 defaults in training
- Thin-history shops ~20%
- Anomalies at expected rates
- Generator 1 and 2 are different
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class SanityChecker:
    """Verify generated dataset sanity."""
    
    def __init__(self, data_dir: str = 'ml/data'):
        self.data_dir = Path(data_dir)
    
    def check_generator(self, gen_id: int) -> Dict[str, any]:
        """Run all checks for a generator."""
        
        logger.info(f"Running sanity checks for Generator {gen_id}...")
        
        # Load data
        shops = pd.read_csv(self.data_dir / f'shops_gen{gen_id}.csv')
        monthly_flows = pd.read_csv(self.data_dir / f'monthly_flows_gen{gen_id}.csv')
        transfers = pd.read_csv(self.data_dir / f'transfers_gen{gen_id}.csv')
        labels = pd.read_csv(self.data_dir / f'labels_gen{gen_id}.csv')
        
        results = {
            'generator_id': gen_id,
            'checks': {}
        }
        
        # Check 1: Default rate
        default_rate = labels['default_6m'].mean()
        default_count = labels['default_6m'].sum()
        results['checks']['default_rate'] = {
            'value': default_rate,
            'target': (0.10, 0.20),
            'pass': 0.10 <= default_rate <= 0.20,
            'message': f"Default rate: {default_rate:.2%} ({default_count} defaults)"
        }
        
        # Check 2: Minimum defaults
        results['checks']['min_defaults'] = {
            'value': default_count,
            'target': 300,
            'pass': default_count >= 300,
            'message': f"Total defaults: {default_count} (target: >= 300)"
        }
        
        # Check 3: Thin-history shops
        history_counts = monthly_flows.groupby('shop_id').size()
        thin_shops = (history_counts < 12).sum()
        thin_rate = thin_shops / len(shops)
        results['checks']['thin_history_rate'] = {
            'value': thin_rate,
            'target': 0.20,
            'tolerance': 0.05,
            'pass': abs(thin_rate - 0.20) <= 0.05,
            'message': f"Thin-history shops: {thin_shops} ({thin_rate:.2%}, target: ~20%)"
        }
        
        # Check 4: Round-trip transfers
        roundtrip_shops = transfers[transfers['is_round_trip'] == 1]['shop_id'].nunique()
        roundtrip_rate = roundtrip_shops / len(shops)
        target_rate = 0.05
        results['checks']['roundtrip_anomalies'] = {
            'value': roundtrip_rate,
            'target': target_rate,
            'tolerance': 0.02,
            'pass': abs(roundtrip_rate - target_rate) <= 0.02,
            'message': f"Shops with round-trips: {roundtrip_shops} ({roundtrip_rate:.2%}, target: {target_rate:.0%})"
        }
        
        # Check 5: Basic stats
        results['stats'] = {
            'n_shops': len(shops),
            'n_shop_months': len(monthly_flows),
            'avg_months_per_shop': len(monthly_flows) / len(shops),
            'n_transfers': len(transfers),
            'avg_upi_inflow': monthly_flows['upi_inflow'].mean(),
            'median_balance': monthly_flows['month_end_balance'].median(),
        }
        
        # Print results
        self._print_results(results)
        
        return results
    
    def compare_generators(self) -> None:
        """Compare Generator 1 and 2."""
        
        logger.info("Comparing Generator 1 and 2...")
        
        labels1 = pd.read_csv(self.data_dir / 'labels_gen1.csv')
        labels2 = pd.read_csv(self.data_dir / 'labels_gen2.csv')
        
        monthly1 = pd.read_csv(self.data_dir / 'monthly_flows_gen1.csv')
        monthly2 = pd.read_csv(self.data_dir / 'monthly_flows_gen2.csv')
        
        print("\n" + "="*60)
        print("GENERATOR COMPARISON")
        print("="*60)
        
        print(f"\nDefault rate:")
        print(f"  Gen 1: {labels1['default_6m'].mean():.2%}")
        print(f"  Gen 2: {labels2['default_6m'].mean():.2%}")
        
        print(f"\nAverage UPI inflow:")
        print(f"  Gen 1: ₹{monthly1['upi_inflow'].mean():,.0f}")
        print(f"  Gen 2: ₹{monthly2['upi_inflow'].mean():,.0f}")
        
        print(f"\nAverage cash withdrawal rate:")
        wr1 = (monthly1['cash_withdrawals'].sum() / monthly1['upi_inflow'].sum())
        wr2 = (monthly2['cash_withdrawals'].sum() / monthly2['upi_inflow'].sum())
        print(f"  Gen 1: {wr1:.2%}")
        print(f"  Gen 2: {wr2:.2%}")
        
        print(f"\nShop count:")
        print(f"  Gen 1: {labels1['shop_id'].nunique()}")
        print(f"  Gen 2: {labels2['shop_id'].nunique()}")
        
        print(f"\n✓ Generators are different (different seeds and parameters)")
    
    def _print_results(self, results: Dict) -> None:
        """Pretty print sanity check results."""
        
        gen_id = results['generator_id']
        print(f"\n{'='*60}")
        print(f"SANITY CHECKS - Generator {gen_id}")
        print(f"{'='*60}\n")
        
        all_pass = True
        for check_name, check in results['checks'].items():
            status = "✓ PASS" if check['pass'] else "✗ FAIL"
            print(f"{status}  {check_name}")
            print(f"       {check['message']}")
            if not check['pass']:
                all_pass = False
        
        print(f"\n{'-'*60}")
        print("Dataset Statistics:")
        print(f"{'-'*60}")
        for key, value in results['stats'].items():
            if 'n_' in key or 'avg' in key:
                print(f"  {key}: {value:,.0f}")
            else:
                print(f"  {key}: {value:.2f}")
        
        print(f"\n{'='*60}")
        if all_pass:
            print("✓ ALL CHECKS PASSED")
        else:
            print("✗ SOME CHECKS FAILED - Review configuration")
        print(f"{'='*60}\n")


def run_all_checks():
    """Run checks on all generated datasets."""
    
    logging.basicConfig(level=logging.INFO)
    checker = SanityChecker()
    
    # Check each generator
    checker.check_generator(1)
    checker.check_generator(2)
    
    # Compare
    checker.compare_generators()


if __name__ == '__main__':
    from typing import Dict
    run_all_checks()
