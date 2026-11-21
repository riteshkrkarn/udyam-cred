# ML Guide for UdyamCred (Tiered Design)

## What Changed

The product is now **tiered**. A shop's tier depends on the evidence it can provide. Loan amount and tranche rules depend on the tier. ML models still score risk and capacity, but tier and amount rules sit on top of them.

---

## The Three Tiers

| Tier | Who | Evidence | Amount Rule |
|---|---|---|---|
| **1** | Below GST limit, no formal documents | Money-side only (UPI, bank, photos, ledger) | Smallest tier, strictly capped |
| **2** | GST filings or long, steady bank history | Adds GSTR-2B matching and longer verified window | Scaled by verified evidence |
| **3** | Udyam registration + repayment record with lender | Adds Udyam and tranche history | Higher tiers, released in tranches |

---

## ML Models

### 1. Credibility Scorecard (Logistic Regression)

**Outputs:**
- `default_probability` (0-1)
- `risk_band` (Low / Moderate / High)
- `confidence` (0-1)

**Performance:**
- Test AUC: **0.61** (modest)
- Train AUC: 0.6163
- Val AUC: 0.5312

**Role:** Source agreement and tier decision support. AUC is modest, so present as a risk signal, not as the sole decision.

### 2. Repayment Capacity Model (Linear Regression)

**Outputs:**
- `safe_monthly_emi` (₹)

**Performance:**
- Test R²: **0.83** (strong on synthetic)
- Test MAE: **₹703**
- Median % error: **1.4%**

**Role:** Sets EMI ceiling. Loan amount rule still takes lowest of: capacity model, tier cap, stock limit.

**Caveat:** R² of 0.83 on synthetic data can appear too good. The synthetic EMI target was generated from the same features, so fit is partly by construction. Real-world accuracy will be lower.

---

## Features

**40 features** total across:
- Cash flow (UPI, deposits, withdrawals, balance, trends)
- GST (turnover, filing rate)
- Reconciliation (sales vs GST gap, correlation)
- Stock (value, composition, turnover days)
- Purchases (bill count, supplier diversity, confirmation rate)
- Vintage (source agreement, earliest signal)
- Anomalies (round-trip transfer rate)

**Important:** Family size is **NOT** a scorecard input. It enters only:
- Household budget calculation
- EMI cap calculation

This allows fairness checks comparing results with and without family size.

---

## Data

### Generators

| Generator | Shops | Months | Default Rate | Purpose |
|---|---|---|---|---|
| **Gen 1** | 5,000 | ~30 per shop | ~15% | Training / Validation |
| **Gen 2** | 1,500 | ~30 per shop | ~12% | Held-out Test |

Different seeds and parameters ensure meaningful test-set split.

### Generated Files

```
ml/ml/data/
├── shops_gen1.csv           (5,000 shops)
├── monthly_flows_gen1.csv   (~150k rows)
├── purchases_gen1.csv
├── stock_snapshots_gen1.csv
├── vintage_signals_gen1.csv
├── transfers_gen1.csv
├── labels_gen1.csv
├── features_gen1.csv        (40 features)
│
├── shops_gen2.csv           (1,500 shops, test set)
├── features_gen2.csv
└── labels_gen2.csv
```

---

## Code

### Training Pipeline
```bash
cd ml
python train_models.py
```

**Output:** `models/` directory with 5 files
- `scorecard.pkl`
- `capacity_model.pkl`
- `scaler_scorecard.pkl`
- `scaler_capacity.pkl`
- `metadata.json`

### Scoring in Production

```python
from scorer import load_ensemble

# Load trained models
ensemble = load_ensemble('ml/models')

# Score a single shop
result = ensemble.score_shop(features_dict)
# Returns: ScoringResult with scorecard and capacity

# Score a batch
batch_results = ensemble.score_batch(df)
# Returns: DataFrame with columns
#   - default_probability
#   - risk_band
#   - scorecard_confidence
#   - safe_emi
```

### Demo & Analysis
```bash
cd ml
python demo_scorecard.py
```

Shows predictions, calibration checks, and analysis by shop type and health.

---

## What Still Needs Building (MVP Stage 2)

### 1. Tier Rules
- **Tier 1 rules:** No GSTR-2B, no Udyam. Amount strictly capped.
- **Tier 2 rules:** Has GSTR-2B or 36+ months bank. Scales by verified window.
- **Tier 3 rules:** Has Udyam + prior repayment record. Tranched.

### 2. Amount Rules
- For each tier, set the cap.
- Loan amount = min(capacity_model, tier_cap, stock_limit).
- Tests: smallest tier must be strictly lower cap.

### 3. Tranche & Stop Rules
- **Release schedule:** Tier 3 releases in tranches based on EMI performance.
- **Stop rule:** Two missed EMIs → freeze further tranches.

### 4. Synthetic Repayment Outcomes
- Current: capacity target (safe EMI) known.
- Missing: sequence of actual EMIs to test tranche stop rules.

### 5. Evaluation Script
**Two main claims to measure:**
- **Claim 1:** Approval rate by tier vs bureau-only baseline (at same default rate).
- **Claim 2:** Tranche outcomes vs single-amount loan (on same repayment outcomes).

### 6. Fairness Check
- Run approval by tier with and without family size.
- Show that score is not making unfair assumptions.

### 7. Sign-Constraint Tests
- More debt → score should not go up.
- Fewer verified records → score should not go up.
- Test across all shops in Gen 1.

---

## Points to Address Before Presenting

### ✓ Scorecard AUC is Weak (0.61)
**Present honestly:** "The scorecard is a supporting signal, not the primary decision lever. Tier and capacity rules carry the weight. The modest AUC reflects the challenge of predicting default from financials alone on new-to-credit shops."

### ✓ Capacity R² Looks Too Good (0.83)
**Explain the construction:** "The synthetic EMI was generated from the same feature set, so the high R² is partly by design. Real-world performance will be lower and should be measured on actual repayment outcomes."

### ✓ Error Rates Against Synthetic Target
**State clearly:** "The 1.4% median error is against the synthetic ground truth, not against real repayments."

### ✓ Gen 1 / Gen 2 Split
**Document for judges:** "Models trained on Gen 1 (5,000 shops, seed=42), tested on Gen 2 (1,500 shops, seed=123, different parameters). This ensures we evaluate on different population parameters."

---

## Next Step

**Build the evaluation script for the two tier claims.** It answers the core claims your design document depends on and is the cheapest way to show measured results.

---

## File References

- `train_models.py` - Training pipeline
- `scorer.py` - Production scoring module
- `demo_scorecard.py` - Demo and analysis
- `models/` - Saved model artifacts
- `ml/data/` - Generated datasets (Gen 1 & Gen 2)
