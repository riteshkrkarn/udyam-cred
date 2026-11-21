# Phase 1-2 ML Claims: Testing & Reproducibility

**Last Updated:** November 21, 2026  
**Test Data:** Gen 2 Synthetic (1,500 shops)  
**Evaluation Status:** ✅ All three claims tested and documented

---

## Quick Start: Run All Tests

```bash
cd ml

# 1. Generate test data (if not already generated)
python -c "from generator import generate_and_save; generate_and_save(generator_id=2, output_dir='ml/data')"

# 2. Run all three claim evaluations
python evaluation_tiers.py                    # Claim 1: Approval rate
python evaluation_tranche_outcomes.py         # Claim 2: Tranches
python evaluation_fairness.py                 # Claim 3: Fairness

# 3. Read the full report
cat CLAIMS_REPORT.md
```

---

## Test Results Summary

| Claim | Status | Key Finding | Caveat |
|-------|--------|-------------|--------|
| **1: Approval Rate** | ✅ Validated on Gen 2 | +354% approvals, 6.3% default | Bureau baseline is weak; synthetic data |
| **2: Tranches** | 🟨 Finding: Underperforms | -42pp worse default than single-amount | Gates may be working as designed; needs real data |
| **3: Fairness** | ✅ Validated on Gen 2 | Zero correlation with family size | Synthetic test weak; code passes but fairness unproven |

---

## Test Data: Gen 2 Generation

**Command:**
```bash
python -c "from generator import generate_and_save; generate_and_save(generator_id=2, output_dir='ml/data')"
```

**Parameters:**
- Seed: 42 (fixed in `generator.py`)
- Shops: 1,500
- Output directory: `ml/ml/data/`

**Generated Files:**
- `tier_assignments_gen2.csv` - Tier (1/2/3) assigned to each shop
- `source_data_gen2.csv` - Multi-source verification (GST, Udyam, UPI agreement scores)
- `verified_windows_gen2.csv` - Months of verified history per source
- `photos_gen2.csv` - Photo evidence metadata
- `features_gen2.csv` - Computed features (1,500 rows)
- `labels_gen2.csv` - Ground truth (default_6m, hidden_health)
- `*_gen2.csv` - Additional supporting data (shops, purchases, transfers, etc.)

**Tier Distribution (Gen 2):**
- Tier 1: 427 shops (28.5%) - 6-12mo bank, no GST
- Tier 2: 783 shops (52.2%) - 12+mo bank + GST
- Tier 3: 290 shops (19.3%) - 24+mo + Udyam + history

---

## Claim 1: Approval Rate vs Bureau Baseline

**Script:** `evaluation_tiers.py`

**What it tests:**
- Tier-based lending (T1 max ₹50k, T2 max ₹250k, T3 max ₹1M)
- Compared against bureau-only baseline (250 total approvals)
- Same assumed default rate (10%)

**Command:**
```bash
python evaluation_tiers.py
```

**Output:**
- `ml/evaluation_claim1_results.csv` - Results by tier
- Console output shows:
  - Approval counts per tier (UdyamCred vs Bureau)
  - Total capital deployed
  - Default rates
  - Per-tier improvements

**Results (Gen 2):**
```
Tier 1: 427 approvals vs 50 bureau (+754.0%)
Tier 2: 783 approvals vs 200 bureau (+291.5%)
Tier 3: 290 approvals vs 80 bureau (+262.5%)
Overall: 1,500 vs 330 (+354.5%)
Default: 6.3% vs 10.0% (-3.7pp)
```

**Caveats:**
1. Bureau baseline rejects ~85% with no credit history - low bar to beat
2. Default rates on synthetic data (generator includes hidden_health feature)
3. Tier distribution may not match real population
4. Assumes perfect tier classification (real tier assignment will have error)

**Real Test Needed:**
- Compare on real applicant population with same bureau score
- Measure actual default on production loans, not synthetic
- Calibrate baseline against actual bureau-only reject rates

---

## Claim 2: Tranches vs Single-Amount Loans

**Script:** `evaluation_tranche_outcomes.py`

**What it tests:**
- Progressive tranches with EMI gates vs single lump-sum disbursement
- Per-application default rate (denominator: applicants, not tranches)
- Simulator models payment behavior (poor/fair/good/excellent health)

**Command:**
```bash
python evaluation_tranche_outcomes.py
```

**Output:**
- `ml/evaluation_claim2_results.csv` - Results by tier and health category
- Console output shows:
  - Tranche funnel (how many reach T1, T2, T3, T4)
  - Default rate comparison
  - Completion rate comparison

**Results (Gen 2):**
```
Aggregate default: Tranche 55% vs Single 13% (TRANCHES WORSE by 42pp)

By Tier:
T1: Tranches match/beat single (good health: 0% vs 5%)
T2: Tranches worse (poor: 100% vs 28%; good: 50% vs 8%)
T3: Tranches worse (poor: 100% vs 20%; good: 60% vs 5%)
```

**Key Finding: Tranches Underperform**

Root cause is **not a bug** (we fixed it), but a **design issue**:

1. **Gates are very restrictive for poor/fair health:**
   - T2 Poor: 2/5 shops pass T1 gate → stuck at 1 tranche instead of 2
   - T3 Fair: 2/5 pass T1, only 1/5 pass T2 → never reach T3
   - Result: fewer tranches disbursed → less capital at risk, but also less lending

2. **Single-amount baselines are assumptions, not real data:**
   - Baseline assumes 28% default for T2-poor single amount
   - But tranches achieve 100% default on what IS disbursed
   - Real question: is this because gates prevent worse outcomes, or because gates freeze people who would succeed?

**Honest Interpretation:**
- ❌ Tranches do NOT enable better lending for poor/fair health (they restrict it)
- ✅ Tranches DO gate access (good for risk control; bad for inclusion)
- ❓ Gates improve overall *risk-adjusted* returns? Unknown without real data.

**Caveats:**
1. Only 5 simulations per scenario (small sample; high variance possible)
2. Single-amount baselines are synthetic assumptions, not calibrated to real data
3. Payment probability models are simplified (don't capture real behavior)
4. Real test must use production repayment data

**Real Test Needed:**
1. Increase simulations to 100+ per scenario
2. Get real single-amount default data (actual loans, not assumptions)
3. Calibrate gate thresholds (test 1-missed, 2-missed, 3-missed EMI triggers)
4. Measure on production: actual EMI gate effectiveness

---

## Claim 3: Fairness (Family Size Excluded)

**Script:** `evaluation_fairness.py`

**What it tests:**
- Correlation between family_size and tier assignment
- Correlation between family_size and default rate
- Credit amount variation by family size

**Command:**
```bash
python evaluation_fairness.py
```

**Output:**
- `evaluation_fairness_results.json` - Full statistical results
- Console output shows:
  - Tier distribution independence test (max proportion difference)
  - Default rate variance by family size
  - Credit amount by family size quartiles

**Results (Gen 2):**
```
Tier distribution max deviation: 7.8% (threshold: <10%) ✓
Default rate std dev by family size: 1.34% (threshold: <5%) ✓
Credit amounts: No meaningful variation by family size ✓
Conclusion: FAIRNESS VALIDATED (on synthetic data)
```

**The Caveat:**
**This test is weak on synthetic data.** The generator does not use family_size as a feature, so zero correlation is *expected* - not evidence of fairness. Code review confirms family_size is never referenced, but simulation fairness is circular.

**Honest Assessment:**
- ✅ Code passes: family_size is not used in tier assignment or rates
- ✅ Simulation passes: no unexpected correlations emerge
- ❓ Real fairness: unknown without production data

**What Real Fairness Test Would Look Like:**
1. Stratified comparison: match shops by cash-flow strength, compare approval/rate across family sizes
2. Budget impact: does household budget accounting differ by family size? (It should, if realistic)
3. Production monitoring: track approval, rate, default, EMI compliance by family size over time

**Caveats:**
1. Synthetic data; generator doesn't use family_size feature
2. Zero correlation expected and uninformative
3. Real fairness requires production monitoring, not simulation

---

## Reproducibility Checklist

- [x] Gen 2 data generated (1,500 shops, seed=42)
- [x] Tier distribution recorded (T1 28.5%, T2 52.2%, T3 19.3%)
- [x] All three evaluation scripts tested
- [x] Results saved to CSVs/JSON
- [x] Caveats documented
- [x] Next steps identified for production validation

**To reproduce exactly:**
```bash
# Step 1: Generate data with fixed seed
cd ml
python -c "from generator import generate_and_save; generate_and_save(generator_id=2, output_dir='ml/data')"

# Step 2: Run evaluations (order doesn't matter)
python evaluation_tiers.py
python evaluation_tranche_outcomes.py
python evaluation_fairness.py

# Step 3: Review results
cat CLAIMS_REPORT.md
```

All tests are deterministic (fixed seeds); output should be identical on re-run.

---

## Key Takeaways for Review

**What we have:** Strong hypotheses on synthetic data showing promise  
**What we need:** Production validation to claim success

| Claim | Synthetic Result | Confidence | Next Step |
|-------|-----------------|------------|-----------|
| Approval | +354% gains | Medium | Test on real bureau-comparable population |
| Tranches | Underperform | Low | Debug gate calibration on real payments |
| Fairness | Zero bias | Low | Monitor production fairness metrics |

**Before judicial/regulatory defense:** All three claims need production data validation.

---

**Generated:** 2026-11-21  
**Author:** ML Evaluation Pipeline  
**Status:** Ready for backend integration & production testing
