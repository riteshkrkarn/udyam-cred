# ML: Synthetic Data Generation and Feature Engineering

This directory contains the data generation and feature engineering pipeline for UdyamCred.

## Overview

The ML pipeline generates synthetic shop financial data with the following architecture:

```
Generator (hidden health) → Monthly flows → Features → Training data
         ↓                                              ↓
    Reconciliation signals                    Scorecard + Capacity model
```

## Components

### 1. `generator_config.py`
Configuration for two synthetic data generators. Each generator has different parameters and seeds to ensure train/test separation.

**Key configurations:**
- **Generator 1**: 5,000 shops, ~30 months history (training/validation split 70/15/15)
- **Generator 2**: 1,500 shops, ~30 months history (held-out test set)

Both generators inject known anomalies:
- **Round-trip transfers**: ~5% of shops (circular money flow)
- **Sales inflation**: ~5% of shops (reported sales exceed inventory)
- **Vintage disagreement**: ~12-15% of shops (conflicting date sources)
- **Supplier mismatches**: ~3-4% of shops (confirmed != billed)

### 2. `generator.py`
Generates realistic synthetic shop data following the business logic:

1. **Hidden health score**: Latent factor determining all financial behavior
   - Normal distribution, clipped to [0, 1]
   - Directly affects default probability and safe EMI

2. **Monthly cash flows**:
   - Base revenue scaled by health and seasonality
   - UPI inflow, cash deposits, withdrawals, balance
   - GST turnover (reconciliation signal)
   - Sales and purchases (for stock check)

3. **Purchases and stock**:
   - Individual supplier bills (with optional confirmation flag)
   - Monthly stock snapshots (value, composition, turnover)

4. **Vintage signals**: Multiple date sources
   - First UPI date, GST registration, Udyam registration
   - First supplier bill, lease start date
   - Injected disagreement for anomaly detection

5. **Transfers**: Counterparty money flows
   - Normal transfers to suppliers
   - Injected round-trip patterns (circular transfers)

6. **Labels**:
   - `default_6m`: Binary label (1 = missed 2+ EMIs in 6 months)
   - `safe_emi_true`: Ground truth safe monthly repayment amount
   - `hidden_health`: Health category for analysis

### 3. `feature_builder.py`
Transforms raw data into ML-ready features as of a point in time (as-of date).

**Feature categories:**

#### Cash flow features (12 features)
- Total/average UPI inflow, standard deviation
- Cash deposits, withdrawals
- Cash withdrawal rate (indicator of owner draws)
- Latest month balance and trend
- Missing data flags for each

#### GST features (4 features)
- Total GST turnover, number of filed returns
- GST filing rate (consistency indicator)

#### Reconciliation features (4 features)
- Reconciliation gap: |sales - GST| / sales
- Gap standard deviation (volatility)
- Sales-GST correlation (do they track together?)

#### Stock features (4 features)
- Average stock value
- Fast-moving vs slow-moving share
- Inventory turnover days

#### Purchase features (4 features)
- Number of supplier bills
- Number of unique suppliers
- Supplier confirmation rate

#### Vintage features (4 features)
- Number of vintage sources available
- Disagreement between sources (days)
- Months since earliest signal

#### Transfer anomaly features (3 features)
- Number of transfers
- Number of round-trip transfers
- Round-trip rate

#### Shop attributes (6 features)
- Shop type (categorical: general_store, pharmacy, electronics, apparel, hardware)
- Shop size (categorical: micro, small, medium)
- Rented vs owned
- Family size
- Shop vintage in months
- Co-borrower score (if available)

**Total: ~50 features with missing data flags**

### 4. `run_generator.py`
Entry point to generate all datasets and build feature matrices.

```bash
# Generate both datasets
python ml/run_generator.py --gen all

# Generate only Generator 1
python ml/run_generator.py --gen 1

# Generate and build features
python ml/run_generator.py --gen all --with-features

# Custom output directory
python ml/run_generator.py --gen all --data-dir /path/to/data
```

### 5. `sanity_checks.py`
Validates that generated data meets requirements.

```bash
python ml/sanity_checks.py
```

**Checks:**
- Default rate between 10-20% ✓
- At least 300 defaults in training ✓
- Thin-history shops ~20% (±5%) ✓
- Round-trip anomalies at ~5% rate ✓
- Generator 1 and 2 are meaningfully different ✓

## Generated Files

### Tables (CSV)

**Generator 1 (`gen1`):**
- `shops_gen1.csv`: Shop attributes (5,000 shops)
- `monthly_flows_gen1.csv`: Monthly financials (~150,000 rows)
- `purchases_gen1.csv`: Individual supplier bills
- `stock_snapshots_gen1.csv`: Monthly stock data
- `vintage_signals_gen1.csv`: Vintage dates from multiple sources
- `transfers_gen1.csv`: Counterparty transfers
- `labels_gen1.csv`: Default labels and ground truth
- `config_gen1.json`: Generator configuration (for reproducibility)

**Generator 2 (`gen2`):**
- Same structure, different parameters and seed

**Features:**
- `features_gen1.csv`: Feature matrix for all shops (~50 columns)
- `features_gen2.csv`: Feature matrix for held-out test set

### Schema

#### shops.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Unique identifier |
| city | string | Location |
| shop_type | string | general_store, pharmacy, electronics, apparel, hardware |
| shop_size | string | micro, small, medium |
| rented_or_owned | string | Business property status |
| vintage_months | int | Months in operation |
| family_size | int | Dependents (affects EMI capacity) |
| co_borrower_score | float | Optional co-borrower credit score |
| synthetic | bool | Always True |

#### monthly_flows.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Reference to shops |
| month | string | YYYY-MM |
| upi_inflow | float | Digital revenue (₹) |
| cash_deposits | float | Bank deposits (₹) |
| cash_withdrawals | float | Owner draws (₹) |
| gst_turnover | float | GST-reported turnover (₹) |
| sales_value | float | Reported sales (₹) |
| purchases_value | float | Total purchases (₹) |
| month_end_balance | float | Account balance (₹) |
| expired_stock_value | float | Waste/shrinkage (₹) |
| gst_filed | bool | GST return filed this month |

#### purchases.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Reference to shops |
| month | string | YYYY-MM |
| supplier_id | string | Supplier identifier |
| bill_amount | float | Bill amount (₹) |
| supplier_credit_days | int | Payment terms (0, 15, 30, 45, 60) |
| supplier_confirmed | bool | Supplier verified bill |

#### stock_snapshots.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Reference to shops |
| month | string | YYYY-MM |
| stock_value | float | Inventory value (₹) |
| fast_moving_share | float | % fast-moving items [0-1] |
| slow_moving_share | float | % slow-moving items [0-1] |
| turnover_days | float | Days to sell inventory |

#### vintage_signals.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Reference to shops |
| first_upi_date | date | YYYY-MM-DD or null |
| gst_registration_date | date | YYYY-MM-DD or null |
| udyam_date | date | YYYY-MM-DD or null |
| first_supplier_bill_date | date | YYYY-MM-DD or null |
| lease_start_date | date | YYYY-MM-DD or null (if rented) |

#### transfers.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Reference to shops |
| counterparty_id | string | Other party identifier |
| month | string | YYYY-MM |
| amount | float | Transfer amount (₹) |
| is_round_trip | bool | 1 if part of circular pattern, 0 otherwise |

#### labels.csv
| Column | Type | Notes |
|--------|------|-------|
| shop_id | string | Reference to shops |
| default_6m | bool | 1 = missed 2+ EMIs in next 6 months |
| safe_emi_true | float | Ground truth safe monthly payment (₹) |
| hidden_health | string | excellent, good, fair, poor |

## Usage

### Step 1: Generate Data
```bash
cd ml
python run_generator.py --gen all --with-features
```

This creates:
- Raw data CSVs for both generators
- Feature matrices for ML training

### Step 2: Run Sanity Checks
```bash
python sanity_checks.py
```

Verify data quality and anomaly injection rates.

### Step 3: Train Models
Use the feature matrices and labels to train:
- **Credibility scorecard** (logistic regression)
- **Repayment capacity model** (regression with bounds)
- **Baseline models** for comparison

### Step 4: Evaluation
- Test on Generator 2 (held-out test set)
- Compare approval rates vs bureau baseline
- Measure round-trip detection rate
- Run fairness audit with/without family size

## Key Properties

### Reproducibility
Each generator has a fixed seed in `generator_config.py`. Datasets can be exactly rebuilt using stored configurations.

### Realism
- Health-driven: All financials follow from hidden health score
- Seasonality: Revenue peaks in Diwali season, drops in monsoon
- Reconciliation: Healthy shops have sales ≈ GST; anomalies show mismatches
- Vintage signals: Multiple sources can disagree (testing reconciliation)

### Anomaly Ground Truth
- Round-trip transfers: Flagged in transfers table
- Sales inflation: Magnitude known (1.2-1.5x multiplier)
- Vintage disagreement: Days disagreement calculated
- Supplier mismatch: Confirmation vs bill mismatch rate known

### Default Prediction
- Driven by health score (decreases default probability)
- Volatility in monthly revenues increases default risk
- Falling balance trend signals distress
- More dependents (family_size) reduces safe EMI

## Statistics (Example)

```
Generator 1 (Training):
- 5,000 shops
- ~150,000 shop-months
- Default rate: 15% (750 defaults)
- Thin-history: 20% (1,000 shops with 6-12 months)
- Average UPI inflow: ₹120,000/month

Generator 2 (Test):
- 1,500 shops
- ~45,000 shop-months
- Default rate: 12% (180 defaults)
- Different seasonality and baseline health
```

## Next Steps

1. **Feature selection**: Which features most predictive?
2. **Scorecard training**: Logistic regression with sign constraints
3. **Capacity modeling**: Predict safe repayment amount
4. **Baseline comparison**: vs UPI-only and bureau-only models
5. **Fairness audit**: With and without family_size

See the main README for the full build plan.
