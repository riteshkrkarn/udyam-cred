# Phase 1-2 ML Data Generation Guide

## Overview

The updated `ml/generator.py` now supports Phase 1-2 tier-based lending system with realistic source data generation. The generator creates synthetic data that mimics:

- **Tier-based classification** (Tier 1, 2, 3 based on verified evidence)
- **Multi-source data** (AA/bank, GST, UPI flows with realistic overlaps)
- **Verified windows** (months where multiple sources overlap)
- **Source agreement scores** (correlation between data sources)
- **Photo verification** (geo-tagged photos with verification status)

## Tier Classification Logic

### Distribution (in test)
- **Tier 1**: 27.6% → Bank data only, 6-12 months, amounts ≤₹50k
- **Tier 2**: 54.0% → Bank + GST, 12-24 months, amounts ≤₹250k
- **Tier 3**: 18.4% → Bank + GST + Udyam + repayment history, 24+ months, amounts ≤₹1M

### Assignment Rules (in `_generate_shops`)
```python
tier_rand = random()
if tier_rand < 0.30:
    tier = TIER_1  # No GST, no Udyam
elif tier_rand < 0.80:
    tier = TIER_2  # Has GST
else:
    tier = TIER_3  # Has GST, Udyam, prior repayment
```

## New Output Files

### 1. `tier_assignments_gen{N}.csv`
Tier assignment for each shop with verification indicators.

**Columns:**
- `shop_id`: Unique shop identifier
- `tier`: 1, 2, or 3
- `has_gst`: Boolean (GST filings available)
- `has_udyam`: Boolean (Udyam registration)
- `has_prior_repayment`: Boolean (Prior repayment history)
- `verified_months`: Number of months with verified data (AA + GST/UPI)
- `source_agreement_score`: 0.6-0.95 correlation between sources

**Sample:**
```
shop_id,tier,has_gst,has_udyam,has_prior_repayment,verified_months,source_agreement_score
shop_01_000000,3,True,True,True,29,0.889
shop_01_000001,2,True,False,False,28,0.950
shop_01_000003,1,False,False,False,8,0.950
```

### 2. `source_data_gen{N}.csv`
Monthly flows from multiple sources (AA, GST, UPI).

**Columns:**
- `shop_id`: Unique shop identifier
- `month`: YYYY-MM format
- `aa_flow`: Account Aggregator / bank flow in ₹ (may be null)
- `gst_flow`: GST turnover in ₹ (may be null, only for Tier 2/3)
- `upi_flow`: UPI inflow in ₹ (may be null)
- `tier`: Tier of the shop (1, 2, or 3)

**Characteristics:**
- **Tier 1**: AA + UPI always, no GST (~95% data completeness)
- **Tier 2**: AA + GST + UPI, 85-95% completeness per source
- **Tier 3**: AA + GST + UPI all available, healthier shops have more data

**Sample:**
```
shop_id,month,aa_flow,gst_flow,upi_flow,tier
shop_01_000000,2024-06,23355.29,36979.20,23355.29,3
shop_01_000000,2024-07,24511.06,38809.18,24511.06,3
shop_01_000000,2024-08,,33910.76,21417.32,3
```

### 3. `verified_windows_gen{N}.csv`
Verified windows (months where AA + GST/UPI overlap) and source agreement.

**Columns:**
- `shop_id`: Unique shop identifier
- `window_start`: First month of verified data (YYYY-MM)
- `window_end`: Last month of verified data (YYYY-MM)
- `months_verified`: Total verified months
- `agreement_score`: Source correlation (0.6-0.95)
- `tier`: Tier of the shop

**Calculation:**
```
Verified month = Month where:
  - AA is available (not null) AND
  - (GST is available OR UPI is available)
```

**Sample:**
```
shop_id,window_start,window_end,months_verified,agreement_score,tier
shop_01_000000,2024-06,2026-10,29,0.889,3
shop_01_000001,2024-06,2026-10,28,0.950,2
shop_01_000003,2024-06,2024-12,8,0.950,1
```

### 4. `photos_gen{N}.csv`
Photo metadata with location, timestamp, and verification status.

**Columns:**
- `shop_id`: Unique shop identifier
- `photo_num`: Photo sequence number (1-5 per shop)
- `photo_type`: Type of photo (exterior, signboard, interior, shop_front, bill_board)
- `location_lat`: Latitude (geo-tagged)
- `location_lng`: Longitude (geo-tagged)
- `timestamp`: ISO 8601 timestamp (last 90 days)
- `verified`: 1 if verified, 0 if not (85% verified in test)

**Sample:**
```
shop_id,photo_num,photo_type,location_lat,location_lng,timestamp,verified
shop_01_000000,1,exterior,12.97,75.04,2026-10-23T10:24:53.808275,1
shop_01_000000,2,signboard,12.96,75.05,2026-09-25T10:24:53.808275,1
shop_01_000001,1,interior,12.98,75.03,2026-09-17T10:24:53.808275,1
```

## Key Statistics (500-shop test)

### Tier Distribution
- Tier 1: 138 shops (27.6%)
- Tier 2: 270 shops (54.0%)
- Tier 3: 92 shops (18.4%)

### Source Agreement Scores
- Mean: 0.910
- Std: 0.049
- Min: 0.731
- Max: 0.950
- Range: 0.6-0.95 as specified

### Verified Months
- Mean: 23.8 months
- Median: 28.0 months
- Reflects realistic data availability

### Photos
- Total: 1,978 photos (3-5 per shop)
- Verified: 1,681 (85.0%)
- Types evenly distributed

## Implementation Details

### Tier Assignment (`_assign_tiers`)
- Called after shops are generated
- Records tier, GST/Udyam/repayment flags

### Source Data Generation (`_generate_source_data`)
- For each shop-month combination:
  - AA flow: 95%+ availability (health-dependent)
  - GST flow: Only for Tier 2/3, 85-95% availability
  - UPI flow: 95%+ availability
- Data completeness varies by shop health score

### Verified Window Calculation (`_calculate_verified_windows`)
- Identifies overlapping months (AA + GST/UPI)
- Calculates source correlation via pairwise comparisons
- Maps correlation [-1, 1] to agreement_score [0.6, 0.95]
- Updates shop metadata with results

### Photo Generation (`_generate_photos`)
- 3-5 photos per shop (random)
- Geo-tagged by city + shop_id + noise
- Recent timestamps (last 90 days)
- 85% verified (configurable)

## Usage

### Generate Full Datasets

```python
from generator import generate_and_save

# Generate and save all 4 Phase 1-2 outputs
generate_and_save(1, output_dir='ml/data')
generate_and_save(2, output_dir='ml/data')
```

### Generate Programmatically

```python
from generator_config import GENERATOR_1_CONFIG
from generator import SyntheticDataGenerator

config = GENERATOR_1_CONFIG  # 5000 shops
generator = SyntheticDataGenerator(config)

(shops, monthly_flows, purchases, stock_snapshots, vintage_signals, 
 transfers, labels, tier_assignments, source_data, verified_windows, 
 photos, metadata) = generator.generate()

# Access Phase 1-2 outputs
print(tier_assignments.head())
print(source_data.head())
print(verified_windows.head())
print(photos.head())
```

## Integration with Backend

### Tier Assignment Input
The backend can use `tier_assignments` to validate tier classification:

```python
# Backend receives: shop_id, verified_months, agreement_score
# Backend calculates: tier based on TIER_1/2/3 rules
# Backend approves: amount based on tier caps

tier_assignment = tier_assignments[
    tier_assignments['shop_id'] == application_shop_id
].iloc[0]

verified_months = tier_assignment['verified_months']
agreement_score = tier_assignment['source_agreement_score']
```

### Source Data for Feature Building
ML pipeline can use source data to:

```python
# Calculate: flow volatility, trend, seasonality
# Detect: anomalies (round-trips, inflation, vintage disagreements)

source_df = source_data[source_data['shop_id'] == shop_id]

# Check overlaps
has_aa = source_df['aa_flow'].notna().any()
has_gst = source_df['gst_flow'].notna().any()
has_upi = source_df['upi_flow'].notna().any()
```

### Photos for Risk Assessment
Backend can use photos to:

```python
# Verify: location consistency
# Assess: shop conditions (from photo types)
# Track: location changes over time

shop_photos = photos[photos['shop_id'] == shop_id]
verified_photo_count = shop_photos['verified'].sum()
photo_diversity = shop_photos['photo_type'].nunique()
```

## Performance Characteristics

### Generation Speed
- 5,000 shops: ~30-45 seconds
- 500 shops: ~3-5 seconds
- Bottleneck: Source agreement score calculation (pairwise correlations)

### Output File Sizes (500 shops)
- `tier_assignments`: 24.5 KB
- `source_data`: 919.3 KB
- `verified_windows`: 24.0 KB
- `photos`: 182.0 KB
- **Total Phase 1-2: ~1.15 MB**

## Configuration Parameters

In `generator_config.py`:

```python
GeneratorConfig(
    generator_id=1,
    n_shops=5000,
    months_per_shop=30,
    # ... existing parameters
    # Phase 1-2 automatically handled by updated generator
)
```

No new config parameters needed - tier distribution is hardcoded:
- 30% Tier 1
- 50% Tier 2
- 20% Tier 3

To change distribution, modify `_generate_shops()`:

```python
tier_rand = self.rng.rand()
if tier_rand < 0.25:  # Changed from 0.30
    tier = Tier.TIER_1
elif tier_rand < 0.75:  # Changed from 0.80
    tier = Tier.TIER_2
else:
    tier = Tier.TIER_3
```

## Testing Checklist

✅ Tier distribution matches expected (30/50/20 or close)
✅ Source agreement scores in range [0.6, 0.95]
✅ Verified windows non-zero for most shops
✅ Photos generated (3-5 per shop)
✅ Location coordinates within city bounds
✅ Source data reflects tier (Tier 1: no GST, etc.)
✅ All 4 CSV files created successfully
✅ No missing values in required fields

## Common Issues

### Issue: All agreement scores = 0.95
**Cause:** No overlapping sources for correlation calculation
**Fix:** Increase data availability in `_generate_source_data`

### Issue: Verified months = 0
**Cause:** Called `_assign_tiers` before `_calculate_verified_windows`
**Fix:** Ensure correct call order: shops → monthly_flows → source_data → verified_windows → tier_assignments

### Issue: Photos have invalid coordinates
**Cause:** City not in `city_lat_map`
**Fix:** Add city to mapping in `_generate_photos`

## Future Enhancements

1. **Tier-appropriate amounts**: Generate `approved_amount` field by tier cap
2. **Tranche schedules**: Generate multi-tranche data for Tier 3
3. **Repayment outcomes**: EMI payment history (on-time/late/missed)
4. **Rate adjustments**: Generate `rate_percent` by tier
5. **Stop rule simulation**: Track missed EMIs and freeze tranches

---

**Last Updated:** 2025-01 | **Generator Version:** Phase 1-2 v1.0
