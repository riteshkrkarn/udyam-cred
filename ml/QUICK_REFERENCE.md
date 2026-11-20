# ML Generator - Quick Reference

## One-Command Generation

```bash
cd ml
pip install -r requirements.txt
python3 run_generator.py --gen all --with-features
python3 sanity_checks.py
```

**Done!** Check `ml/data/` for all output files.

## Commands

| Command | Purpose |
|---------|---------|
| `python3 run_generator.py --gen all` | Generate both datasets |
| `python3 run_generator.py --gen 1` | Generator 1 only (training) |
| `python3 run_generator.py --gen 2` | Generator 2 only (test) |
| `python3 run_generator.py --gen all --with-features` | Generate + build features |
| `python3 sanity_checks.py` | Verify data quality |
| `python3 demo.py` | Quick test (100 shops) |

## Output Files

### Raw Data (CSV)
- `shops_gen1.csv` - Shop attributes
- `monthly_flows_gen1.csv` - Monthly financials
- `purchases_gen1.csv` - Supplier bills
- `stock_snapshots_gen1.csv` - Inventory data
- `vintage_signals_gen1.csv` - Date sources
- `transfers_gen1.csv` - Counterparty transfers
- `labels_gen1.csv` - Default labels + safe EMI

### Processed Data
- `features_gen1.csv` - ML-ready features (~50 features)
- `config_gen1.json` - Generator configuration

### Same for Generator 2 (gen2)

## Quick Load & Explore

```python
import pandas as pd

# Load data
shops = pd.read_csv('ml/data/shops_gen1.csv')
flows = pd.read_csv('ml/data/monthly_flows_gen1.csv')
features = pd.read_csv('ml/data/features_gen1.csv')
labels = pd.read_csv('ml/data/labels_gen1.csv')

# Merge and analyze
df = features.merge(labels[['shop_id', 'default_6m']], on='shop_id')

# Check default rate
print(f"Default rate: {labels['default_6m'].mean():.1%}")

# Check feature counts
print(f"Features: {len(features.columns)}")
```

## Data Structure

```
One shop over time:
shop_id        family_size  vintage_months  health_score (hidden)
|
├─ Monthly flows (12-36 months)
│  ├─ UPI inflow, cash deposits, GST turnover
│  ├─ Sales, purchases, month-end balance
│  └─ Stock snapshots (fast/slow moving, turnover days)
│
├─ Purchases (multiple supplier bills per month)
│  └─ Bill amount, supplier credit days, confirmation
│
├─ Transfers (counterparty money flows)
│  └─ Round-trip flag (for anomaly detection)
│
├─ Vintage signals (multiple date sources)
│  └─ First UPI, GST, Udyam, supplier, lease dates
│
└─ Label
   ├─ default_6m (binary: 0/1)
   ├─ safe_emi_true (ground truth safe EMI)
   └─ hidden_health (for analysis)
```

## Feature Categories (~50 total)

| Category | Count | Key Features |
|----------|-------|--------------|
| Cash flow | 12 | UPI inflow, deposits, withdrawals, balance trend |
| GST | 4 | Turnover, filing rate, consistency |
| Reconciliation | 4 | Sales vs GST gap, correlation |
| Stock | 4 | Value, composition, turnover days |
| Purchases | 4 | Bill count, supplier diversity, confirmations |
| Vintage | 4 | Source agreement, disagreement days |
| Transfers | 3 | Round-trip count, anomaly rate |
| Shop attrs | 6 | Type, size, family_size, co-borrower |

*Plus missing-data flags for each major category.*

## Anomalies (with ground truth)

| Anomaly | Rate | Ground Truth |
|---------|------|--------------|
| Round-trip transfers | 5% | `is_round_trip` column |
| Sales inflation | 5% | Multiplication factor (1.2-1.5x) |
| Vintage disagreement | 12% | Days disagreement calculated |
| Supplier mismatch | 3% | Confirmation vs bill mismatch |

## Dataset Stats

### Generator 1 (Training)
```
Shops:           5,000
Months/shop:     ~30
Total rows:      ~150,000
Default rate:    ~15%
Defaults:        ~750 (>300 required ✓)
Thin-history:    ~20% ✓
```

### Generator 2 (Test)
```
Shops:           1,500
Default rate:    ~12% (different from Gen 1 ✓)
For held-out evaluation
```

## Train/Validation Split

```python
import numpy as np

# Split by shop (not row!)
unique_shops = features['shop_id'].unique()
np.random.shuffle(unique_shops)

n = len(unique_shops)
train_shops = unique_shops[:int(0.7*n)]
val_shops = unique_shops[int(0.7*n):int(0.85*n)]
test_shops = unique_shops[int(0.85*n):]

X_train = features[features['shop_id'].isin(train_shops)]
X_val = features[features['shop_id'].isin(val_shops)]
X_test = features[features['shop_id'].isin(test_shops)]
```

## What's Hidden

| Item | Where | Purpose |
|------|-------|---------|
| `health_score` | `metadata` dict (generator only) | Drives all financials |
| `default_probability` | `metadata` | True default driver |
| `safe_emi_true` | `labels_gen1.csv` | Ground truth for capacity model |
| `hidden_health` | `labels_gen1.csv` | For fairness audit |

## Common Issues

| Issue | Solution |
|-------|----------|
| Missing `pandas`/`numpy` | `pip install -r requirements.txt` |
| Default rate not 10-20% | Adjust `default_rate_base` in config |
| Too few/many anomalies | Adjust injection rates in config |
| Out of memory | Generate one generator at a time |
| Reproducibility | Same seed = same data (stored in JSON) |

## Next: Model Training

1. Load `features_gen1.csv` + `labels_gen1.csv`
2. Select features (exclude ID and flags starting with `_flag`)
3. Split: 70% train, 15% val, 15% test (by shop, not row)
4. Train:
   - **Scorecard**: Logistic regression (sign-constrained)
   - **Capacity**: Linear/tree regression (monotone constraints)
5. Evaluate on Generator 2

See README.md for full architecture.
