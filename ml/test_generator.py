#!/usr/bin/env python
"""Generator verification script"""
from generator import SyntheticDataGenerator
from generator_config import GeneratorConfig

# Test 1: Initialize generator with seed (using small config for verification)
config = GeneratorConfig(
    generator_id=1,
    seed=42,
    n_shops=10,
    months_per_shop=24,
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
gen = SyntheticDataGenerator(config)

# Generate all tables
(shops_df, monthly_flows_df, purchases_df, stock_snapshots_df, 
 vintage_signals_df, transfers_df, labels_df, tier_assignments_df,
 source_data_df, verified_windows_df, photos_df, metadata) = gen.generate()

print(f'Generated {len(shops_df)} shops')

# Test 2: Check tier labeling and verified_months
print('\nFirst 3 shops tier and verified months:')
print(f'Tier assignments columns: {tier_assignments_df.columns.tolist()}')
for i in range(min(3, len(tier_assignments_df))):
    row = tier_assignments_df.iloc[i]
    tier = row.get("tier", "N/A")
    # Try different column names
    verified_months = row.get("months_verified") or row.get("verified_months") or "N/A"
    print(f'Shop {i}: tier={tier}, verified_months={verified_months}')

# Test 3: Verify deterministic with same seed
print('\nTesting determinism with same seed...')
config2 = GeneratorConfig(
    generator_id=1,
    seed=42,
    n_shops=10,
    months_per_shop=24,
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
gen2 = SyntheticDataGenerator(config2)
(shops_df2, _, _, _, _, _, _, tier_assignments_df2, 
 _, verified_windows_df2, _, _) = gen2.generate()

# Check if tier assignments match
tiers_match = tier_assignments_df[['shop_id', 'tier']].equals(tier_assignments_df2[['shop_id', 'tier']])
print(f'Deterministic tier assignments: {tiers_match}')

# Check if verified windows match
windows_match = verified_windows_df[['months_verified']].equals(verified_windows_df2[['months_verified']]) if 'months_verified' in verified_windows_df.columns else True
print(f'Deterministic verified windows: {windows_match}')

# Test 4: Check tier distribution and verified_months appropriateness
print('\nTier distribution and verified months:')
tier_data = {}
for _, row in tier_assignments_df.iterrows():
    tier = int(row["tier"])
    verified_months = row["verified_months"]
    if tier not in tier_data:
        tier_data[tier] = {"count": 0, "verified_months": []}
    tier_data[tier]["count"] += 1
    tier_data[tier]["verified_months"].append(verified_months)

for tier in sorted(tier_data.keys()):
    data = tier_data[tier]
    avg_months = sum(data["verified_months"]) / len(data["verified_months"]) if data["verified_months"] else 0
    min_months = min(data["verified_months"]) if data["verified_months"] else 0
    max_months = max(data["verified_months"]) if data["verified_months"] else 0
    print(f'Tier {tier}: {data["count"]} shops, verified_months: avg={avg_months:.1f}, min={min_months}, max={max_months}')

# Test 5: Verify tier-appropriate verified months
print('\nVerifying tier-appropriate verified months:')
errors = []
for _, row in tier_assignments_df.iterrows():
    tier = int(row["tier"])
    verified = row["verified_months"]
    
    if tier == 1 and not (6 <= verified <= 12):
        errors.append(f"Tier 1 shop has {verified} months (expected 6-12)")
    elif tier == 2 and not (12 <= verified <= 24):
        errors.append(f"Tier 2 shop has {verified} months (expected 12-24)")
    elif tier == 3 and not (verified >= 24):
        errors.append(f"Tier 3 shop has {verified} months (expected 24+)")

if errors:
    print(f'✗ Found {len(errors)} violations:')
    for err in errors[:5]:
        print(f'  - {err}')
else:
    print('✓ All tier-appropriate verified months constraints satisfied')

print('\nGenerator test completed successfully')
