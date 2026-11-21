#!/usr/bin/env python
"""Test script for Phase 1-2 data generation."""

from generator_config import GeneratorConfig
from generator import generate_and_save
import os

# Create test config with 500 shops
test_config = GeneratorConfig(
    generator_id=1,
    seed=42,
    n_shops=500,
    months_per_shop=30,
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

# Monkey patch to use test config
import generator as gen_module
def mock_get_config(generator_id):
    return test_config
gen_module.get_config = mock_get_config

# Generate and save
print('Generating dataset with 500 shops...')
generate_and_save(1, 'ml/data')
print('\n✓ Generation complete!')

# Verify output files
print('\nOutput files:')
for f in sorted(os.listdir('ml/data')):
    size = os.path.getsize(f'ml/data/{f}') / 1024  # KB
    print(f'  {f}: {size:.1f} KB')
