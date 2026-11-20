# Getting Started with Data Generation

This guide walks through generating synthetic datasets for UdyamCred.

## Prerequisites

```bash
# Python 3.8+
python3 --version

# Install dependencies
cd ml
pip install -r requirements.txt
```

## Quick Start

### Generate All Datasets (with features)

```bash
cd ml
python3 run_generator.py --gen all --with-features
```

This creates:
- Generator 1 data (training/validation): 5,000 shops, ~150,000 monthly rows
- Generator 2 data (held-out test): 1,500 shops, ~45,000 monthly rows
- Feature matrices for both

Expected output:
```
============================================================
GENERATING DATASET: Generator 1
============================================================

Generating dataset with config: generator_id=1, n_shops=5000, seed=42
Generated 5000 shops with 152743 monthly rows
Default rate: 15.20%
Anomalies - Roundtrip: 247, Sales inflation: 252, Vintage disagreement: 601

=== SANITY CHECKS ===
Generator: 1
Shops: 5000
Monthly rows: 152743
...
✓ Saved features_gen1.csv

============================================================
GENERATING DATASET: Generator 2
============================================================
...
```

### Generate Individual Datasets

```bash
# Generator 1 only
python3 run_generator.py --gen 1

# Generator 2 only
python3 run_generator.py --gen 2

# With custom output directory
python3 run_generator.py --gen all --data-dir /path/to/data
```

### Run Sanity Checks

```bash
cd ml
python3 sanity_checks.py
```

Expected output:
```
============================================================
SANITY CHECKS - Generator 1
============================================================

✓ PASS  default_rate
       Default rate: 15.20% (760 defaults)
✓ PASS  min_defaults
       Total defaults: 760 (target: >= 300)
✓ PASS  thin_history_rate
       Thin-history shops: 1003 (20.06%, target: ~20%)
✓ PASS  roundtrip_anomalies
       Shops with round-trips: 247 (4.94%, target: 5%)

============================================================
✓ ALL CHECKS PASSED
============================================================
```

## Output Files

All files are saved to `ml/data/` by default:

### Raw Data Tables
```
shops_gen1.csv
├─ 5,000 shops with attributes (city, type, size, family_size, etc.)

monthly_flows_gen1.csv
├─ ~150,000 rows (shop-month)
├─ UPI inflow, cash deposits, GST turnover, balance, etc.

purchases_gen1.csv
├─ Individual supplier bills
├─ Includes optional supplier confirmations

stock_snapshots_gen1.csv
├─ Monthly inventory data per shop
├─ Stock value, composition, turnover days

vintage_signals_gen1.csv
├─ Multiple vintage date sources per shop
├─ UPI, GST, Udyam, supplier, lease dates

transfers_gen1.csv
├─ Counterparty transfers
├─ Ground truth round-trip label

labels_gen1.csv
├─ Default label (binary: 0/1)
├─ Ground truth safe EMI
├─ Hidden health category
```

### Feature Matrices
```
features_gen1.csv
├─ ~5,000 rows (one per shop)
├─ ~50 features: cash flow, GST, reconciliation, stock, vintage, anomalies
├─ Includes missing data flags for each major feature group

config_gen1.json
└─ Generator configuration (for reproducibility)
```

## Data Characteristics

### Generator 1 (Training/Validation)
```
Shops:              5,000
Monthly rows:       ~150,000 (avg 30 months per shop)
Default rate:       ~15%
Thin-history:       ~20% (6-12 months only)
Round-trip anomalies: ~5% (247 shops)
Sales inflation:    ~5% (252 shops)
Vintage disagreement: ~12% (601 shops)
```

### Generator 2 (Held-out Test)
```
Shops:              1,500
Monthly rows:       ~45,000
Default rate:       ~12% (different base rate)
Thin-history:       ~18%
Different seasonality and parameters than Gen 1
```

## Example Usage

### Load and Explore Data

```python
import pandas as pd

# Load tables
shops = pd.read_csv('ml/data/shops_gen1.csv')
monthly = pd.read_csv('ml/data/monthly_flows_gen1.csv')
features = pd.read_csv('ml/data/features_gen1.csv')
labels = pd.read_csv('ml/data/labels_gen1.csv')

# Merge for analysis
df = features.merge(labels[['shop_id', 'default_6m']], on='shop_id')

# Check default rate by health
print(df.groupby('hidden_health')['default_6m'].mean())
```

### Split for Training

```python
# 70% train, 15% validation, 15% test
train_idx = np.random.choice(len(df), size=int(0.7*len(df)), replace=False)
remaining = np.setdiff1d(np.arange(len(df)), train_idx)
val_idx = remaining[:len(remaining)//2]
test_idx = remaining[len(remaining)//2:]

X_train = X.iloc[train_idx]
X_val = X.iloc[val_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_val = y.iloc[val_idx]
y_test = y.iloc[test_idx]
```

### Train a Simple Model

```python
from sklearn.linear_model import LogisticRegression

# Select features (excluding identifiers and flags)
feature_cols = [col for col in features.columns 
                if not col.startswith('shop') and '_flag' not in col]

X = features[feature_cols].fillna(0)
y = labels[['default_6m']].values.ravel()

# Train logistic regression
model = LogisticRegression()
model.fit(X_train, y_train)

# Evaluate
print(f"Train AUC: {model.score(X_train, y_train):.3f}")
print(f"Test AUC: {model.score(X_test, y_test):.3f}")
```

## Troubleshooting

### Missing dependencies

```bash
pip install -r requirements.txt
```

### Data not generating

Check logs for errors:
```bash
python3 run_generator.py --gen 1 2>&1 | head -50
```

### Sanity checks failing

If checks fail, they indicate issues with:
- **Default rate**: Adjust `default_rate_base` in `generator_config.py`
- **Thin history**: Adjust `keep_thin_history_rate`
- **Anomalies**: Adjust injection rates (roundtrip_rate, sales_inflation_rate, etc.)

Then regenerate and verify again.

### Memory issues

For large-scale generation, generate one generator at a time:
```bash
python3 run_generator.py --gen 1
python3 run_generator.py --gen 2
```

## Architecture Details

### How Data is Generated

```
1. Generate shops
   ├─ Random attributes (type, size, city)
   ├─ Hidden health score (latent factor, N(0.6, 0.25))
   └─ Shop metadata (family_size, vintage_months)

2. For each shop-month:
   ├─ Apply seasonality (peaks: Nov, Dec, Jan)
   ├─ Generate revenue (base × health × seasonality × noise)
   ├─ Calculate cash flows (UPI, deposits, withdrawals)
   ├─ Generate purchases from suppliers
   ├─ Create stock snapshot
   └─ Record transfers

3. Inject anomalies:
   ├─ Round-trip transfers (A→B→A) in ~5%
   ├─ Sales inflation (1.2-1.5x) in ~5%
   ├─ Vintage disagreement (±180 days) in ~12%
   └─ Supplier confirmation mismatches in ~3%

4. Generate labels:
   ├─ Default probability ∝ (1 - health)
   ├─ Safe EMI ∝ health × household_factor
   └─ Ground truth for model training
```

### Feature Engineering

Features are built as-of a specific date, looking back `lookback_months`:

```
Cash flow     → UPI inflow, deposits, withdrawals, balance trend
GST           → Turnover, filing rate
Reconciliation→ Sales vs GST gap, correlation
Stock         → Value, composition, turnover days
Purchases     → Bill count, supplier diversity, confirmation rate
Vintage       → Source agreement, earliest signal
Anomalies     → Round-trip transfer rate
Shop attrs    → Type, size, family size, co-borrower score
```

Each feature group includes a missing-data flag indicating data unavailability.

## Next Steps

1. **Verify data quality**: Run sanity_checks.py
2. **Explore features**: Load CSVs and analyze distributions
3. **Train models**: Scorecard (logistic regression), capacity (regression)
4. **Evaluate on Gen 2**: Test held-out performance
5. **Build decision pipeline**: Combine scorecard + capacity + rules

See `ml/README.md` for full technical documentation.
