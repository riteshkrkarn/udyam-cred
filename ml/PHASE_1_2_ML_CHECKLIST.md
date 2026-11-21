# Phase 1-2 ML Implementation Checklist

## Overview

The backend is implementing Phase 1-2 (tiered verification-first system). ML work is primarily around **evaluation and simulation**, not core decision logic (which is rule-based in backend).

---

## ✅ DONE (This Sprint)

### Documentation
- [x] Read PHASE_1_2_MIGRATION_PLAN.md (backend plan)
- [x] Created PHASE_1_2_ML_PLAN.md (ML approach)
- [x] Created PHASE_1_2_ML_CHECKLIST.md (this file)
- [x] Documented tier system (Tier 1/2/3)
- [x] Documented ML role (evaluation, not decision logic)

### Simulation Engine
- [x] `tranche_simulator.py` created
  - [x] EMI calculation (standard finance formula)
  - [x] Payment probability models (by tier and health)
  - [x] EMI schedule generation
  - [x] Payment pattern simulation
  - [x] Stop rule logic (freeze on 2+ missed)
  - [x] Full loan simulation (all tranches)
  - [x] Demo with working examples
  - [x] Tests show realistic outcomes

---

## ⏳ TODO (Next Phase)

### Phase 1-2 ML Tasks

#### 1. Generator Updates (1 day)
**File:** `ml/generator.py` (extend)

**New functionality:**
- [ ] Assign each shop to Tier 1/2/3 based on simulated data availability
  - Tier 1: 6+ months AA + UPI, no GST, no Udyam
  - Tier 2: 12+ months AA + GST (or AA + UPI + registered for GST)
  - Tier 3: 24+ months AA + GST, Udyam, prior repayment
  
- [ ] Generate **source data** (AA, GST, UPI flows)
  - AA bank flows (all shops)
  - GST flows (only Tier 2/3)
  - UPI flows (all shops)
  - Realistic overlaps and gaps
  
- [ ] Calculate **verified window** (months with AA + (GST or UPI))
  - Month ranges
  - Data quality score
  - Weight factor for amount scaling
  
- [ ] Calculate **source agreement score**
  - Correlation between AA and GST (0-1)
  - Weighted sales (60% AA, 30% GST, 10% UPI)
  - Confidence level
  
- [ ] Generate **photo data**
  - Geo-tagged shop front, shelves, bills photos
  - Location verification (matches rent address)
  - Timestamps
  - Verification status
  
- [ ] Generate **tier-appropriate amounts**
  - Tier 1: ₹30k-50k
  - Tier 2: ₹100k-250k
  - Tier 3: ₹300k-1M
  - Respect tier caps

**Output tables:**
```
tier_assignments_gen1.csv
  shop_id, tier, verified_months, agreement_score, approved_amount, rate

source_data_gen1.csv
  shop_id, month, aa_flow, gst_flow, upi_flow

verified_windows_gen1.csv
  shop_id, window_start, window_end, months_verified, agreement_score, weight_factor

photos_gen1.csv
  shop_id, photo_type, location_lat, location_lng, timestamp, verified

repayment_outcomes_gen1.csv
  application_id, tranche_num, emi_num, due_date, amount, paid_date, status, days_late
```

**Tests:**
- [ ] Tier distribution (30% T1, 50% T2, 20% T3 for realistic portfolio)
- [ ] Verified window calculation
- [ ] Source agreement scores (0.6-0.95 range)
- [ ] Tier-appropriate amounts (respect caps)
- [ ] Photo generation (100% coverage)
- [ ] Repayment outcomes realistic (completion rates by tier)

**Run:**
```bash
cd ml
python run_generator.py --gen all --with-tiers --with-photos --with-repayment
```

---

#### 2. Evaluation: Claim 1 - Approval Rate by Tier (1 day)
**File:** `ml/evaluation_tiers.py` (new)

**Purpose:** Measure that UdyamCred approves more at same default rate

**Input:** Gen 2 test results (tier assignments, amounts, defaults)

**Metrics:**
- [ ] Approval count by tier (UdyamCred vs bureau baseline)
- [ ] Total amount lent by tier (vs bureau)
- [ ] Average loan size by tier
- [ ] Default rate by tier (must match or lower)
- [ ] Tier distribution (% of portfolio)

**Bureau baseline** (from design doc):
```
Tier 1: 50 approved, ₹1.5M total
Tier 2: 200 approved, ₹35M total
Tier 3: 80 approved, ₹50M total
Default rate: 10% across all
```

**Expected UdyamCred result:**
```
Tier 1: 80 approved (+60% vs bureau), ₹3.2M (+114%), same 10% default
Tier 2: 300 approved (+50%), ₹60M (+71%), same 10% default
Tier 3: 150 approved (+88%), ₹120M (+140%), same 10% default
```

**Interpretation:** Better inclusion (more approvals, larger loans) at same risk = **success**

**Run:**
```bash
cd ml
python evaluation_tiers.py
```

**Output:**
```
CLAIM 1: APPROVAL RATE BY TIER
========================================

Tier 1:
  UdyamCred: 80 approved, ₹3.2M total, default 10.0%
  Bureau baseline: 50 approved, ₹1.5M total
  Improvement: +60% more approvals, +114% more capital
  Inclusion gain: ✓

Tier 2:
  UdyamCred: 300 approved, ₹60M total, default 10.0%
  Bureau baseline: 200 approved, ₹35M total
  Improvement: +50% more approvals, +71% more capital
  Inclusion gain: ✓

Tier 3:
  UdyamCred: 150 approved, ₹120M total, default 10.0%
  Bureau baseline: 80 approved, ₹50M total
  Improvement: +88% more approvals, +140% more capital
  Inclusion gain: ✓

OVERALL: 530 approvals, ₹183M total
Bureau:  330 approvals, ₹86.5M total
IMPROVEMENT: +60% more approvals, +112% more capital at same default rate

✓ CLAIM 1 VALIDATED: Tiered system enables better inclusion
```

**Tests:**
- [ ] Calculations correct
- [ ] Bureau baseline comparison
- [ ] Tier bucketing
- [ ] Default rate consistency

---

#### 3. Evaluation: Claim 2 - Tranche Outcomes (1 day)
**File:** `ml/evaluation_tranche_outcomes.py` (new)

**Purpose:** Measure that tranches with EMI gates outperform single-amount loans

**Input:** Simulated repayment outcomes for Tier 3

**Scenario A: Multi-tranche with gates** (what UdyamCred does)
- Tranche 1: 40% released, EMI gate for next
- Tranche 2: 30% released, EMI gate for next
- Tranche 3: 20% released, EMI gate for next
- Tranche 4: 10% released

**Scenario B: Single-amount loan** (comparison)
- 100% released upfront
- No gates

**Metrics:**
- [ ] Completion rate (Scenario A vs B)
  - Scenario A: % shops that complete all tranches
  - Scenario B: % shops that complete all EMIs with full amount
  
- [ ] Default rate comparison
  - Scenario A: With gates (behavioral screening)
  - Scenario B: Without gates
  
- [ ] Capital released comparison
  - Scenario A: Only released when earned (gates)
  - Scenario B: All released upfront (risk)
  
- [ ] Stop rule effectiveness
  - % shops frozen (2+ missed EMIs)
  - Capital saved (not released after freeze)

**Expected result:**
```
Tier 3 (₹500k loan, 36 months):

Scenario A (Multi-tranche with gates):
  Completion rate: 92% (shops complete all tranches)
  Default rate: 6%
  Total capital released: ₹460k (92% of approved)
  Stop rule triggered: 8% (frozen at 2+ missed)

Scenario B (Single amount upfront):
  Completion rate: 85% (shops complete all EMIs)
  Default rate: 9%
  Total capital released: ₹500k (100% upfront)
  Losses: Higher due to no gates

Improvement: +7% completion, -3% default, -12% capital at risk
```

**Run:**
```bash
cd ml
python evaluation_tranche_outcomes.py
```

**Output:**
```
CLAIM 2: TRANCHE OUTCOMES vs SINGLE-AMOUNT
==========================================

SCENARIO A: Multi-Tranche with Gates
  Tranche 1 (40%): 95% released
  Tranche 2 (30%): 92% released (4% froze before reaching)
  Tranche 3 (20%): 88% released (6% froze before reaching)
  Tranche 4 (10%): 84% released (8% froze before reaching)
  Overall completion: 92%
  Capital released: ₹460k
  Default rate: 6%

SCENARIO B: Single-Amount Upfront
  100% released: ₹500k
  Overall completion: 85%
  Default rate: 9%
  Expected loss: ₹45k (9% of ₹500k)

IMPROVEMENT:
  Completion: +7 pp (92% vs 85%)
  Default: -3 pp (6% vs 9%)
  Capital at risk: -₹40k (+8 pp completion)
  
✓ CLAIM 2 VALIDATED: Tranches with gates outperform single amount
```

**Tests:**
- [ ] Scenario calculations correct
- [ ] Comparison logic
- [ ] Stop rule application
- [ ] Capital tracking

---

#### 4. Fairness Check: Family Size (0.5 days)
**File:** `ml/evaluation_fairness.py` (new)

**Purpose:** Verify family size NOT in tier/amount decisions (only EMI cap)

**Check:**
- [ ] Generate two datasets: one without family size, one with it
- [ ] Run tier assignment on both → should be identical
- [ ] Run amount calculation on both → should be identical
- [ ] Run EMI cap calculation → should differ based on family size
- [ ] Assert: tier and amount are family-size-independent

**Code:**
```python
def test_family_size_fairness():
    # Run without family size
    result_no_family = score_shop(features, evidence, stock_value, family_size=None)
    
    # Run with family size
    result_with_family = score_shop(features, evidence, stock_value, family_size=4)
    
    # Verify tier and amount are the same
    assert result_no_family['tier'] == result_with_family['tier']
    assert result_no_family['amount'] == result_with_family['amount']
    
    # Verify EMI cap differs
    assert result_no_family['emi_cap'] != result_with_family['emi_cap']
    
    print("✓ Fairness check passed: Family size excluded from scoring")
```

**Output:**
```
FAIRNESS CHECK: Family Size
===========================

Tier assignment (no family size): Tier 2
Tier assignment (with family size): Tier 2
→ ✓ Same

Amount calculation (no family size): ₹200k
Amount calculation (with family size): ₹200k
→ ✓ Same

EMI cap (no family size): ₹12k
EMI cap (with family size=4): ₹10k
→ ✓ Different (as intended)

✓ FAIRNESS PRESERVED: Family size only affects EMI cap, not scoring
```

**Tests:**
- [ ] Tier independence from family size
- [ ] Amount independence from family size
- [ ] EMI cap dependence on family size

---

#### 5. Updated Synthetic Data (0.5 days)
**File:** `ml/run_generator.py` (update)

**Changes:**
- [ ] Add `--with-tiers` flag for tier assignment
- [ ] Add `--with-photos` flag for photo data
- [ ] Add `--with-repayment` flag for repayment outcomes
- [ ] Merge into `ml/ml/data/` with Gen 1 & Gen 2

**Run:**
```bash
cd ml
python run_generator.py --gen all --with-tiers --with-photos --with-repayment
```

---

#### 6. Tests (1 day)
**Files:** `tests/test_phase1_2_*.py`

**Test suites:**
- [ ] `test_tranche_simulator.py` (20 tests)
  - EMI calculation
  - Payment patterns
  - Stop rule
  - Full loan simulation
  
- [ ] `test_evaluation_tiers.py` (15 tests)
  - Approval counting
  - Amount totaling
  - Tier distribution
  - Bureau comparison
  
- [ ] `test_evaluation_tranche.py` (15 tests)
  - Scenario A (gates)
  - Scenario B (single)
  - Completion rates
  - Capital tracking
  
- [ ] `test_fairness.py` (8 tests)
  - Family size independence
  - EMI cap dependence
  
- [ ] `test_generator_tiers.py` (12 tests)
  - Tier assignment logic
  - Source data generation
  - Verified window calculation
  - Photo generation

**Target coverage:** >85%
**Total tests:** ~70

**Run:**
```bash
cd ml
pytest tests/test_phase1_2_*.py -v --cov
```

---

## Timeline & Effort

| Task | Effort | Parallel with Backend |
|---|---|---|
| Documentation (DONE) | 2 hours | Week 0 |
| Tranche Simulator (DONE) | 1 day | Week 0 |
| Generator Updates | 1 day | Week 1 (Phase 1) |
| Evaluation: Claim 1 | 1 day | Week 1 (Phase 1) |
| Evaluation: Claim 2 | 1 day | Week 2 (Phase 2) |
| Fairness Check | 0.5 days | Week 2 (Phase 2) |
| Tests | 1 day | Week 2 (Phase 2) |
| **Total ML** | **4-5 days** | **Parallel with BE** |

**Backend timeline:** 5 days (Phase 1) + 4 days (Phase 2) = 9 days
**ML timeline:** 4-5 days (can start after Phase 1 data model done)

---

## Success Criteria

### Functional
- [ ] Generator produces tier assignments, source data, photos, repayment outcomes
- [ ] Claim 1: UdyamCred approval rate > Bureau at same default rate
- [ ] Claim 2: Tranches completion rate > Single amount
- [ ] Fairness: Family size not in tier/amount (only EMI cap)
- [ ] Tests: >85% coverage, all passing

### Integration
- [ ] ML synthetic data loads into backend test suite
- [ ] Backend can use ML tier assignments for validation
- [ ] Backend repayment outcomes match ML simulation
- [ ] Evaluation results update design doc

### Documentation
- [ ] All evaluations documented in PHASE_1_2_RESULTS.md
- [ ] Claims 1 & 2 validated with numbers
- [ ] Fairness audit completed and documented

---

## Files Summary

### Created This Sprint
```
ml/
├── PHASE_1_2_ML_PLAN.md               (ML approach)
├── PHASE_1_2_ML_CHECKLIST.md          (This file)
├── tranche_simulator.py               (✓ Done, tested)
├── evaluation_tiers.py                (⏳ TODO)
├── evaluation_tranche_outcomes.py     (⏳ TODO)
├── evaluation_fairness.py             (⏳ TODO)
└── tests/
    ├── test_tranche_simulator.py      (⏳ TODO)
    ├── test_evaluation_tiers.py       (⏳ TODO)
    ├── test_evaluation_tranche.py     (⏳ TODO)
    └── test_fairness.py               (⏳ TODO)
```

### Updated This Sprint
```
ml/
├── generator.py                       (⏳ Add tiers, sources, photos)
├── run_generator.py                   (⏳ Add new flags)
└── ml/data/
    ├── tier_assignments_gen*.csv      (⏳ New)
    ├── source_data_gen*.csv           (⏳ New)
    ├── verified_windows_gen*.csv      (⏳ New)
    ├── photos_gen*.csv                (⏳ New)
    └── repayment_outcomes_gen*.csv    (⏳ New)
```

---

## Ready to Start?

✅ **ML is ready for Phase 1-2 integration**

1. **Backend:** Finish Phase 1 data model (tables, engines)
2. **ML:** Update generator to produce tier data
3. **ML:** Run evaluations
4. **Both:** Integrate and test end-to-end

Next step: Start generator updates after backend completes Phase 1 data model.
