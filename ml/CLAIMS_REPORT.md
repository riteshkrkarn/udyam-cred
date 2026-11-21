# Phase 1-2 ML Claims Report: Honest Assessment

**Date:** November 21, 2026  
**Data:** Gen 2 Synthetic (1,500 shops)  
**Status:** All claims tested; results documented with caveats

---

## CLAIM 1: Better Approval at Same Risk ✅ EVIDENCE, BUT CAVEAT REQUIRED

### What We Tested
- Tier-based lending (T1/T2/T3) vs bureau-only baseline
- Same assumed default tolerance (10%)
- Gen 2 synthetic data

### Results (Gen 2 Synthetic)
| Metric | UdyamCred | Bureau | Gain |
|--------|----------|--------|------|
| **Approvals** | 1,500 | 330 | +354.5% |
| **Capital** | ₹454M | ₹86.5M | +425% |
| **Default Rate** | 6.3% | 10.0% | -3.7pp ✓ |

### The Finding
✅ **Approval gains are real**: 354% more loans approved  
✓ **Default rates are lower**: 6.3% vs assumed 10%  
⚠️ **BUT: Bureau baseline is a strawman**

### The Caveat
Bureau-only systems reject ~85% of SMEs with no credit history. So *any* system that approves more will look better. This is not evidence that tiered verification is better—only that it's more inclusive.

**Honest reframe:** "On synthetic data with perfect tier classification, tiered verification approves 3.5x more loans while maintaining 6.3% default. Real-world gains will be smaller due to classification error and different risk distributions."

### Real Test Needed
1. **Stronger baseline:** Compare against a simple UPI-only or cash-flow rule, not just bureau
2. **Fixed default comparison:** "At 6.3% default rate, bureau approves X%; UdyamCred approves Y%"
3. **Production validation:** Test on real applicants, not synthetic data

### CSV Output
- `evaluation_claim1_results.csv` - Tier-by-tier breakdown

---

## CLAIM 2: Tranches Outperform Single-Amount ⚠️ NOT YET PROVEN

### What We Tested
- Tranche lending (progressive disbursement with EMI gates) vs single-amount
- Per-application default rate (denominator: applicants, not tranches)
- Payment probability models from tranche simulator

### Results (Gen 2 Synthetic, 5 simulations per scenario)

**Default Rate by Tier:**
| Tier | Health | Tranche | Single | Gap |
|------|--------|---------|--------|-----|
| T1 | Poor | 60% | 35% | -25pp |
| T1 | Good | 20% | 10% | -10pp |
| T2 | Poor | 100% | 28% | -72pp |
| T2 | Excellent | 0% | 3% | +3pp |
| T3 | Poor | 100% | 20% | -80pp |
| T3 | Good | 60% | 5% | -55pp |

**Aggregate:** Tranche default = 55% vs Single = 13% (WORSE by 42pp)

### The Bug We Found (and Fixed)
**Original bug:** Counted per-*tranche* metrics (if 10 tranches disbursed across 5 apps, denominator = 10).  
**Fix:** Now counts per-*application* metrics (5 apps = denominator 5).

After fix, the problem persists: **tranches genuinely underperform in simulation**.

### Root Cause Analysis
The issue is not code; it's **design conflict**:
1. **Gates are too strict** for poor/fair health borrowers
   - T2 Poor: only 2/5 pass T1 gate → stuck with 1 tranche instead of 2
   - T3 Poor: only 0/5 pass T2 gate → no progressive disbursement
2. **Single-amount baselines are unrealistic** (drawn from assumptions, not real data)
   - Generator assumes 35% default for T1-poor single amount
   - But tranches actually achieve 60% default on exposed amount
3. **Real question:** Gates *should* restrict risky borrowers (freeze them before they lose more money). So poor results on poor/fair health may be **intended**.

### What This Finding Means
- ❌ Tranches do NOT reduce default on poor/fair health borrowers
- ✅ Tranches DO gate access (good: prevents harm; bad: doesn't expand lending)
- ❓ Gates improve *risk-adjusted* returns (approve fewer, but safer)? Unknown.

### Real Test Needed
1. Get real single-amount default data (not assumptions)
2. Calibrate gates to find sweet spot: approve enough (inclusion) vs freeze enough (safety)
3. Test on production: measure actual EMI gate effectiveness on real payment patterns
4. Compare total loss: ($ approved × default%) for tranches vs single-amount

### CSV Output
- `evaluation_claim2_results.csv` - Per-tier, per-health scenario results

**Verdict: DESIGN MAY BE WORKING AS INTENDED, but synthetic simulation alone doesn't prove gates help lending outcomes.**

---

## CLAIM 3: Fairness (Family Size Excluded) ✅ EVIDENCE, BUT WEAK TEST

### What We Tested
- Correlation between family_size and tier assignment
- Correlation between family_size and default rate
- Credit amount variation by family size quartile

### Results (Gen 2 Synthetic)
| Metric | Result | Threshold | Pass |
|--------|--------|-----------|------|
| Tier assignment max deviation | 7.8% | <10% | ✅ |
| Default rate std dev by family size | 1.34% | <5% | ✅ |
| Credit amount correlation | ~0 | Any | ✅ |

### The Finding
✅ **Family size does NOT predict tier or approval**  
✓ **No meaningful variance in outcomes by household size**

### The Caveat
**This test is circular on synthetic data.** The generator does not use family size as a feature, so zero correlation is expected. This doesn't prove fairness works in real data—only that the code doesn't reference family size (which we already knew).

**Honest assessment:** "Code review confirms family_size is not used in tier assignment or scoring. Simulation confirms no unexpected correlation appears. Real fairness test: compare approval/EMI across real family sizes on production data."

### Stronger Test Needed
1. **Stratified comparison:** Group shops by cash-flow strength, compare approval rates across family-size groups within each stratum
2. **Budget impact:** Does accounting for household budget differently based on family size affect approvals? (It should, if budgets are real)
3. **Production monitoring:** Track approval, default, EMI compliance by family size after launch

### CSV Output
- `evaluation_fairness_results.json` - Statistical test results

**Verdict: CODE PASSES BASIC FAIRNESS TEST, but real-world fairness requires production data.**

---

## Summary Table: Honest Assessment

| Claim | Test Result | Evidence | Caveats | Status |
|-------|------------|----------|---------|--------|
| **Approval rate** | +354% on Gen 2 | Strong | Bureau baseline is strawman; synthetic data; real test needed on production | 🟨 PROMISING |
| **Tranches work** | -42pp default gap | Genuine (not a bug) | Gates may be working as intended (freeze risky); unclear if good for lending; needs real data | 🟨 UNCLEAR |
| **Fairness** | Zero correlation | Expected | Synthetic data has no family_size features; code test only, not fairness test | 🟨 PASSES CODE, UNPROVEN FAIRNESS |

---

## Reproducibility & Seeds

**Gen 2 Generation:**
```bash
cd ml
python -c "from generator import generate_and_save; generate_and_save(generator_id=2, output_dir='ml/data')"
```
- Seed: 42 (implicit in generator.py)
- Shops: 1,500
- Output: 8 CSVs in `ml/ml/data/` (tier_assignments, source_data, verified_windows, photos, etc.)

**Claim 1 (Approval Rate):**
```bash
python evaluation_tiers.py
# Output: ml/evaluation_claim1_results.csv
```

**Claim 2 (Tranches):**
```bash
python evaluation_tranche_outcomes.py
# Output: ml/evaluation_claim2_results.csv
# Note: Uses simulator with seed=42, 5 simulations per scenario
```

**Claim 3 (Fairness):**
```bash
python evaluation_fairness.py
# Output: evaluation_fairness_results.json
```

---

## Next Steps (Priority Order)

### 1. Fix Claim 2: Understand Gate Design
- [ ] Print funnel at each gate level (how many stuck at T1, how many reach T2)
- [ ] Calculate total capital available per scenario
- [ ] Decide: are gates meant to freeze risky borrowers, or enable progression?
- [ ] If freeze: measure cost of freeze (default prevented vs lending lost)

### 2. Validate Claim 1 on Real Data
- [ ] Get production bureau baseline (actual rejects with no history)
- [ ] Compare UdyamCred approval rate vs bureau on same applicant population
- [ ] Measure default on real repayment, not synthetic

### 3. Strengthen Fairness Test
- [ ] Create stratified comparison: match shops by cash flow, compare approval across family sizes
- [ ] Track real household budget differences; confirm they don't affect tier/rate
- [ ] Set up production monitoring for fairness metrics

### 4. Documentation
- [ ] Update README with test methodology and caveats
- [ ] Record seeds, shop counts, and reproducible commands
- [ ] Keep Gen 1/Gen 2 separation clear (no tuning on Gen 2)

---

## Conclusion

**All three claims show promise on synthetic data, but require production validation before being tested against rigorous standards.** The findings are:

1. **Tiered verification looks more inclusive** (354% more approvals), but on synthetic data with a weak baseline. Real test: does it improve approval/default trade-off vs smarter alternatives?

2. **Tranches underperform in simulation**, possibly by design (gates freeze risky borrowers). Real test: do gates reduce total loss, or just lending volume?

3. **Fairness looks good in code**, but synthetic test doesn't measure real fairness. Real test: production monitoring across family sizes.

**Bottom line:** These are good *hypotheses* worth testing in production. They are not yet *proven claims* suitable for judicial or regulatory defense. Test on real data before claiming success.

---

**Report generated:** 2026-11-21  
**Test data:** Gen 2 Synthetic (1,500 shops)  
**Evaluation scripts:** `evaluation_tiers.py`, `evaluation_tranche_outcomes.py`, `evaluation_fairness.py`
