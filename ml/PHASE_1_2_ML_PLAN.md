# ML Component for Phase 1-2: Tiered Verification-First System

## Overview

The backend is migrating from generic credit scoring (Stage 2) to a **verification-first, tiered-lending system** with multi-tranche gates and photo evidence. The ML component must support this new architecture.

## What Changes for ML

### Old (Stage 2)
- Single risk band (Low/Moderate/High)
- Capacity model → EMI → loan amount
- Generic features (40 features)
- Single disbursement
- Family size in scorecard (fairness issue)

### New (Phase 1-2)
- Tier-based (Tier 1/2/3) driven by **verified data**, not model
- Source agreement score (% agreement between AA, GST, UPI)
- Verified window (months where multiple sources overlap)
- Multi-tranche with gates (EMI gates unlock next tranche)
- Tranche release only if previous tranche EMIs on-time
- Stop rule: 2 missed EMIs freeze further tranches
- Industry rate + tier adjustment (not ML-driven)
- Family size only in EMI cap (fairness preserved)

## ML Responsibilities (New)

The tiered system is **primarily rule-based, not ML-based**:

```
Verification sources (AA, GST, UPI) → Source agreement score (rule)
                                    ↓
                     Verified window (rule)
                                    ↓
        Tier assignment (rule-based, not ML)
                                    ↓
              Amount = tier_cap × verified_weight
                                    ↓
        Rate = industry_rate + tier_adjustment (rule)
                                    ↓
             Tranche gates (EMI record, rule)
```

**ML is NOT used for:**
- Tier assignment (it's 100% based on verified data availability)
- Amount calculation (it's based on tier cap and verified window)
- Rate calculation (it's industry rate + policy adjustment)
- Tranche release (it's based on EMI performance, not prediction)

**ML IS used for (Future):**
- Anomaly detection (round-trip transfers, bill inflation, vintage disagreement)
- Repayment outcome prediction (will borrower miss EMIs?)
- Fraud detection (photo authenticity, false claims)

## ML Data Generation Changes

### Current Synthetic Data (Stage 2)
- 40 features (cash flow, GST, reconciliation, stock, vintage, anomalies)
- Default label (0/1 for 6-month default)
- Health category (excellent/good/fair/poor)

### New Synthetic Data (Phase 1-2)
- **Tier assignment** (1/2/3 based on source data availability)
- **Source data** (AA, GST, UPI monthly flows with overlaps)
- **Verified window** (months where AA + (GST or UPI) available)
- **Source agreement score** (0-1 correlation between sources)
- **Photo verification** (3-5 geo-tagged photos per shop)
- **Tranche schedule** (4-6 tranches per shop)
- **Repayment history** (EMI payments, on-time/late/missed)
- **Tier-appropriate amounts** (₹50k for Tier 1, ₹250k for Tier 2, ₹1M for Tier 3)

### New Fields in Synthetic Data

#### By Shop
```
shop_id
tier (1/2/3)
verified_months
source_agreement_score
location_verified (true/false)
photo_count
approved_amount
rate_percent
```

#### By Month (new)
```
shop_id, month
aa_bank_flow (₹) [only if AA available]
gst_flow (₹) [only if GST registered]
upi_flow (₹) [always]
```

#### Repayment History (new)
```
application_id
tranche_num
emi_num
due_date
amount (₹)
paid_date (null if missed)
payment_status (ontime/late/missed/bounced)
days_late (0 if on-time, else > 0)
```

## Phase 1-2 ML Work

### 1. Update Synthetic Data Generator

**File:** `ml/generator.py` (extend)

**Changes:**
- Assign each shop to Tier 1/2/3 based on data availability
- Generate **source data** (AA, GST, UPI with realistic overlaps)
  - Tier 1: AA + UPI for 6-12 months, no GST
  - Tier 2: AA + GST + UPI for 12-24 months
  - Tier 3: AA + GST + UPI for 24+ months
- Calculate **verified window** (months where AA + (GST or UPI))
- Calculate **source agreement score** (correlation between sources)
- Generate **photo data** (locations, timestamps, verification status)
- Generate **tier-appropriate amounts** (respect tier caps)

**New Output Tables:**
```
source_data_gen1.csv:
  shop_id, month, aa_flow, gst_flow, upi_flow

verified_windows_gen1.csv:
  shop_id, window_start, window_end, months_verified, agreement_score

photos_gen1.csv:
  shop_id, photo_type, location_lat, location_lng, timestamp, verified

repayment_outcomes_gen1.csv:
  application_id, tranche_num, emi_num, due_date, amount, paid_date, status, days_late

tier_assignments_gen1.csv:
  shop_id, tier, verified_months, agreement_score, approved_amount, rate
```

**Tests:**
- Tier distribution (should match real expectations: ~30% T1, ~50% T2, ~20% T3)
- Verified window calculation
- Source agreement scores (should be 0.6-0.95 range)
- Tier-appropriate amounts (T1: ≤50k, T2: ≤250k, T3: ≤1M)

### 2. Tranche Outcome Simulation

**File:** `ml/tranche_simulator.py` (new)

**Functionality:**
- Simulate repayment outcomes for each tranche
- Model probability of on-time/late/missed payments
- Model probability of 2+ missed EMIs (triggers stop rule)

**Inputs:**
```python
{
  "tier": 2,
  "approved_amount": 200000,
  "rate": 14.0,
  "tenor_months": 24,
  "hidden_health": "good",  # From generator
  "tranche_num": 1
}
```

**Output:**
```python
{
  "emi_schedule": [
    {"emi_num": 1, "amount": 9200, "due_date": "2025-01-20"},
    ...
  ],
  "repayment_outcomes": [
    {"emi_num": 1, "status": "ontime", "paid_date": "2025-01-15"},
    {"emi_num": 2, "status": "late", "paid_date": "2025-02-22", "days_late": 4},
    ...
  ],
  "missed_emi_count": 1,
  "completed_all_emis": true,
  "eligible_for_next_tranche": true  # missed_emi_count < 2
}
```

**Logic:**
- EMI = P × [r(1+r)^n] / [(1+r)^n - 1]
- on-time probability = 0.85 + 0.1 × health_score (80-95% depending on tier/health)
- missed probability = 1 - on_time
- days_late = exponential(0, 30) if late

**Tests:**
- EMI calculation correct
- Probability distribution reasonable
- Stop rule (missed ≥2 freezes tranches)

### 3. Tier-Based Evaluation

**File:** `ml/evaluation_tiers.py` (new)

**Evaluate Claim 1: Approval Rate by Tier vs Baseline**

```python
def evaluate_approval_by_tier(results_df):
    """
    Compare UdyamCred tier-based approval vs bureau baseline.
    
    At same default rate, UdyamCred should approve more and lend more.
    """
    
    # Group by tier
    for tier in [1, 2, 3]:
        tier_data = results_df[results_df['tier'] == tier]
        
        approved_count = len(tier_data)
        total_amount = tier_data['approved_amount'].sum()
        avg_amount = tier_data['approved_amount'].mean()
        default_rate = tier_data['default_6m'].mean()
        
        # Compare to bureau baseline (from doc)
        bureau_count = BUREAU_BASELINE[tier]['approved']
        bureau_amount = BUREAU_BASELINE[tier]['total_lent']
        
        print(f"Tier {tier}:")
        print(f"  UdyamCred: {approved_count} approved, ₹{total_amount:,.0f}, default {default_rate:.1%}")
        print(f"  Bureau:    {bureau_count} approved, ₹{bureau_amount:,.0f}")
        print(f"  Improvement: {((approved_count - bureau_count) / bureau_count) * 100:.1f}% more approvals")
    
    # Overall stats
    print(f"\nOverall:")
    print(f"  Total approved: {len(results_df)}")
    print(f"  Average loan: ₹{results_df['approved_amount'].mean():,.0f}")
    print(f"  Default rate: {results_df['default_6m'].mean():.1%}")
```

**Metrics:**
- Approval count by tier (vs bureau)
- Total amount lent by tier (vs bureau)
- Average loan size by tier
- Default rate by tier
- Tier distribution (% of portfolio in each tier)

**Expected Result:** More approvals and larger amounts at same default rate → proof of better inclusion

### 4. Tranche Outcome Evaluation

**File:** `ml/evaluation_tranche_outcomes.py` (new)

**Evaluate Claim 2: Tranche Outcomes**

```python
def evaluate_tranche_outcomes(simulated_repayments):
    """
    Compare multi-tranche (with gates) vs single-amount loans.
    
    Hypothesis: Tranches with EMI gates reduce default by screening.
    """
    
    tier3_shops = simulated_repayments[simulated_repayments['tier'] == 3]
    
    # Scenario A: Multi-tranche with gates
    scenario_a = tier3_shops[tier3_shops['eligible_for_next_tranche'] == True]
    completion_rate_a = scenario_a['completed_all_emis'].mean()
    
    # Scenario B: Single amount (no gates)
    scenario_b = tier3_shops  # All got full amount upfront
    completion_rate_b = scenario_b['completed_all_emis'].mean()
    
    print(f"Tier 3 Tranche Outcomes:")
    print(f"  Multi-tranche with gates: {completion_rate_a:.1%} completed all EMIs")
    print(f"  Single amount (baseline): {completion_rate_b:.1%} completed all EMIs")
    print(f"  Improvement: {((completion_rate_a - completion_rate_b) / completion_rate_b) * 100:.1f}%")
    
    # Amount released analysis
    scenario_a_amount = scenario_a['released_amount'].sum()
    scenario_b_amount = scenario_b['approved_amount'].sum()
    
    print(f"\n  Amount released (multi-tranche): ₹{scenario_a_amount:,.0f}")
    print(f"  Amount approved (single): ₹{scenario_b_amount:,.0f}")
    print(f"  Capital preservation: {((scenario_b_amount - scenario_a_amount) / scenario_b_amount) * 100:.1f}%")
```

**Metrics:**
- Completion rate with gates vs without
- Default rate with gates vs without
- Capital released vs capital approved
- Stop rule effectiveness (% of frozen due to 2 missed)

**Expected Result:** Tranches with gates > single amount completion rate → proof of behavioral impact

### 5. Fairness Check (Preserved)

**File:** `ml/evaluation_fairness.py` (update)

**New Check:** Family size NOT in scorecard (only in EMI cap)

```python
def evaluate_fairness_family_size(results_df_with_no_family_size, 
                                   results_df_with_family_size_in_cap):
    """
    Verify that family size doesn't affect tier or amount decision.
    Only EMI cap is affected.
    """
    
    # Compare tier assignments
    tier_diff = (results_df_with_no_family_size['tier'] == 
                 results_df_with_family_size_in_cap['tier']).all()
    
    # Compare amounts
    amount_diff = (results_df_with_no_family_size['approved_amount'] == 
                   results_df_with_family_size_in_cap['approved_amount']).all()
    
    # Only EMI cap should differ
    emi_cap_diff = (results_df_with_no_family_size['emi_cap'] != 
                    results_df_with_family_size_in_cap['emi_cap']).any()
    
    assert tier_diff, "Family size should NOT affect tier"
    assert amount_diff, "Family size should NOT affect amount"
    assert emi_cap_diff, "Family size SHOULD affect EMI cap"
    
    print("✓ Fairness check passed: Family size excluded from scoring")
```

## ML Support for Phase 1-2

### New ML Deliverables

1. **Updated synthetic data** with tier assignments, source data, verified windows, repayment outcomes
2. **Tranche outcome simulator** for modeling repayment behavior
3. **Tier-based evaluation script** (Claim 1: approval by tier)
4. **Tranche evaluation script** (Claim 2: tranche outcomes)
5. **Fairness check** (family size preserved)
6. **Tests** for all new modules

### What ML Does NOT Do (Phase 1-2)

- Tier assignment (rules in backend)
- Amount calculation (rules in backend)
- Rate calculation (rules in backend)
- Tranche release gates (repayment tracking in backend)

### What Remains from Stage 2 (if needed)

- Scorecard (AUC 0.61) - available but NOT used in Phase 1-2
- Capacity model (R² 0.83) - available but NOT used in Phase 1-2
- Features (40 features) - still available for future anomaly detection

## Timeline

**Phase 1-2 ML Work:**
- Week 1: Update synthetic data generator (Tier assignments, source data)
- Week 1: Tranche simulator (repayment outcomes)
- Week 2: Evaluation scripts (Claim 1, Claim 2, fairness)
- Week 2: Tests and verification

**Effort:** ~2-3 days (parallel with backend Phase 1-2)

## Files to Create/Update

### New Files
- `ml/tranche_simulator.py` - Simulate repayment outcomes
- `ml/evaluation_tiers.py` - Evaluate tier-based approval
- `ml/evaluation_tranche_outcomes.py` - Evaluate tranche outcomes vs single amount
- `ml/PHASE_1_2_ML_PLAN.md` - This file

### Updated Files
- `ml/generator.py` - Add tier assignment, source data, verified window, photos, repayment
- `ml/run_generator.py` - Run new generator with Phase 1-2 outputs
- `ml/evaluation_fairness.py` - Add family size fairness check

### Tests
- `tests/test_tranche_simulator.py` - Tranche outcome simulation
- `tests/test_evaluation_tiers.py` - Tier evaluation
- `tests/test_evaluation_tranche.py` - Tranche evaluation

## Integration Points

**Backend uses ML for:**
1. Initial synthetic data for testing Phase 1-2
2. Evaluation results (Claim 1, Claim 2) for design doc
3. Repayment outcome simulation (for tranche gates logic)

**Backend provides ML:**
1. Real tier assignments (for model validation later)
2. Real repayment outcomes (for accuracy checks)
3. Real approved amounts by tier (for comparison to synthetic)

## Success Criteria

- ✅ Synthetic data reflects Phase 1-2 architecture (tiers, sources, windows)
- ✅ Tranche simulator produces realistic repayment outcomes
- ✅ Claim 1 shows improved approval at same default rate
- ✅ Claim 2 shows tranches outperform single amount
- ✅ Family size fairness maintained (not in scoring)
- ✅ All tests pass (>85% coverage)

---

## Ready to Begin ML Phase 1-2 Work?

Start with updating synthetic data generator to support the new tiered architecture.
