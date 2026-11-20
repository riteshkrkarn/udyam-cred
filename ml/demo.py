"""
Quick demo: Generate a small sample dataset and show what it looks like.

Generates a tiny dataset (100 shops, 3 months) for quick verification.
"""

import pandas as pd
import numpy as np
from generator import SyntheticDataGenerator
from generator_config import GeneratorConfig


def demo():
    """Generate small demo dataset and show samples."""
    
    print("\n" + "="*60)
    print("UDYAMCRED SYNTHETIC DATA GENERATOR - DEMO")
    print("="*60 + "\n")
    
    # Create tiny config for fast demo
    demo_config = GeneratorConfig(
        generator_id=0,
        seed=999,
        n_shops=100,
        months_per_shop=3,
        health_mean=0.6,
        health_std=0.25,
        seasonality_amplitude=0.25,
        seasonality_peak_months=[11, 12, 1],
        default_rate_base=0.15,
        default_volatility_weight=0.3,
        default_trend_weight=0.2,
        roundtrip_rate=0.05,
        sales_inflation_rate=0.05,
        vintage_disagreement_rate=0.12,
        supplier_mismatch_rate=0.03,
        keep_thin_history_rate=0.20,
    )
    
    print("Generating demo dataset (100 shops, 3 months)...\n")
    
    generator = SyntheticDataGenerator(demo_config)
    shops, flows, purchases, stock, vintage, transfers, labels, metadata = generator.generate()
    
    # Display samples
    print("SHOPS (first 5):")
    print("-" * 60)
    print(shops[['shop_id', 'city', 'shop_type', 'shop_size', 'family_size', 'vintage_months']].head())
    
    print("\n\nMONTHLY FLOWS (first 5):")
    print("-" * 60)
    cols_display = ['shop_id', 'month', 'upi_inflow', 'gst_turnover', 'month_end_balance']
    print(flows[cols_display].head())
    
    print("\n\nSTOCK SNAPSHOTS (first 5):")
    print("-" * 60)
    print(stock[['shop_id', 'month', 'stock_value', 'turnover_days']].head())
    
    print("\n\nPURCHASES (first 5):")
    print("-" * 60)
    print(purchases[['shop_id', 'supplier_id', 'bill_amount', 'supplier_confirmed']].head())
    
    print("\n\nVINTAGE SIGNALS (first 3):")
    print("-" * 60)
    print(vintage[['shop_id', 'first_upi_date', 'gst_registration_date']].head(3))
    
    print("\n\nLABELS (first 5):")
    print("-" * 60)
    print(labels[['shop_id', 'default_6m', 'safe_emi_true', 'hidden_health']].head())
    
    # Stats
    print("\n\n" + "="*60)
    print("DATASET STATISTICS")
    print("="*60)
    print(f"\nShops:                  {len(shops)}")
    print(f"Monthly rows:           {len(flows)}")
    print(f"Avg months per shop:    {len(flows) / len(shops):.1f}")
    print(f"Purchases:              {len(purchases)}")
    print(f"Transfers:              {len(transfers)}")
    print(f"\nDefault rate:           {labels['default_6m'].mean():.1%}")
    print(f"Average safe EMI:       Rs {labels['safe_emi_true'].mean():,.0f}")
    print(f"\nAnomalies:")
    print(f"  Round-trip shops:     {sum(1 for m in metadata.values() if m.has_roundtrip)} ({len([m for m in metadata.values() if m.has_roundtrip]) / len(shops):.1%})")
    print(f"  Sales inflation:      {sum(1 for m in metadata.values() if m.has_sales_inflation)}")
    print(f"  Vintage disagreement: {sum(1 for m in metadata.values() if m.has_vintage_disagreement)}")
    
    print(f"\nAverage monthly stats:")
    print(f"  UPI inflow:         Rs {flows['upi_inflow'].mean():,.0f}")
    print(f"  GST turnover:       Rs {flows['gst_turnover'].mean():,.0f}")
    print(f"  Month-end balance:  Rs {flows['month_end_balance'].mean():,.0f}")
    print(f"  Stock value:        Rs {stock['stock_value'].mean():,.0f}")
    
    print("\n" + "="*60)
    print("✓ DEMO COMPLETE - Data generation working correctly!")
    print("="*60 + "\n")
    
    # Show how to use
    print("Next steps:")
    print("1. Run full generation:")
    print("   python3 run_generator.py --gen all --with-features")
    print("\n2. Verify sanity checks:")
    print("   python3 sanity_checks.py")
    print("\n3. See documentation:")
    print("   - GETTING_STARTED.md for quick start")
    print("   - README.md for full details")
    print()


if __name__ == '__main__':
    demo()
