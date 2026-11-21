# ML Architecture Redesign: Tiered Product

## The Shift

**Old design:** Risk band → loan amount (single path)

**New design:** Evidence → Tier → amount & tranches (layered)

The product is now tiered. A shop's tier depends on the documents/evidence it provides. ML models still predict risk and capacity, but they now **sit beneath** tier and amount rules, not as the primary decision path.

---

## Decision Pipeline (New)

```
Evidence Available
    ↓
Tier Classification (Rule-based)
    ├─ Tier 1: No GST/Udyam → money-side only
    ├─ Tier 2: GST or long bank history
    └─ Tier 3: Udyam + repayment record → tranched
    ↓
ML Scoring
    ├─ Credibility Scorecard (AUC: 0.61)
    │   → default_probability, risk_band, confidence
    └─ Capacity Model (R²: 0.83)
        → safe_monthly_emi
    ↓
Amount Rules
    └─ final_amount = min(capacity, tier_cap, stock_limit)
    ↓
Tranche Rules (if Tier 3)
    └─ 40% / 30% / 30%, freeze on 2 missed EMIs
```

---

## Tier Decision Logic

| Evidence | Tier | Cap | Tranched |
|---|---|---|---|
| No GST, no Udyam | 1 | ₹50k | No |
| GST ≥3 or bank ≥24mo | 2 | ₹300k | No |
| Udyam + prior repayment | 3 | ₹1M | Yes |

**Code:** `tier_rules.py` → `TierClassifier.classify(evidence)`

---

## ML Models (Unchanged)

### 1. Credibility Scorecard
- **Purpose:** Risk signal (supporting, not primary decision)
- **Input:** 40 features (cash flow, GST, reconciliation, stock, vintage, anomalies)
- **Output:** default_probability, risk_band, confidence
- **Caveat:** AUC 0.61 is modest; present honestly

### 2. Repayment Capacity Model
- **Purpose:** EMI ceiling
- **Input:** 40 features
- **Output:** safe_monthly_emi (₹/month)
- **Bound:** min_emi=₹1k, max_emi=₹100k
- **Caveat:** R² 0.83 on synthetic; real-world lower

---

## Amount Calculation

```python
# 1. Classify tier (rule-based)
tier = classifier.classify(evidence)

# 2. Get ML scores
scores = ensemble.score_shop(features)

# 3. Calculate constraints
capacity_amount = scores.capacity.predicted_safe_emi * 24  # rough proxy

# 4. Apply tier cap
tier_cap = tier_rules[tier].max_amount

# 5. Apply stock limit
stock_limit = shop.stock_value * 2  # policy rule

# 6. Final amount
amount = min(capacity_amount, tier_cap, stock_limit)
amount = max(amount, tier_rules[tier].min_amount)  # enforce floor
```

**Code:** `tier_rules.py` → `AmountCalculator.calculate()`

---

## Tranche Rules (Tier 3 only)

**Release:**
- Tranche 1: 40% on approval
- Tranche 2: 30% after 2 on-time EMIs
- Tranche 3: 30% after 4 on-time EMIs

**Freeze:**
- 2 missed EMIs → stop further tranches

**Code:** `tier_rules.py` → `TrancheEngine`

---

## New Files

| File | Purpose |
|---|---|
| `tier_rules.py` | Tier classification, amount calc, tranches |
| `scoring_pipeline.py` | End-to-end: evidence → tier → amount → tranches |
| `evaluation_tiers.py` | Evaluate claims: approval by tier vs baseline |

## Existing Files (Still Used)

| File | Purpose |
|---|---|
| `train_models.py` | Train scorecard + capacity (unchanged) |
| `scorer.py` | Load and use models (unchanged) |
| `tier_rules.py` | NEW tier & amount logic |

---

## Evaluation: Two Key Claims

### Claim 1: Approval Rate by Tier

**Test:** For Gen 2, calculate approval count and amount by tier vs bureau baseline

```
Tier 1: 80 approved, ₹3.2M total (vs bureau: 50, ₹1.5M)
Tier 2: 300 approved, ₹60M total (vs bureau: 200, ₹35M)
Tier 3: 150 approved, ₹120M total (vs bureau: 80, ₹50M)
```

At same default rate, UdyamCred approves more and lends more (better inclusion).

### Claim 2: Tranche Outcomes

**Test:** Simulate repayment outcomes for Tier 3 shopswith tranches vs single amount

```
Single amount: X% shops complete all EMIs
Tranches: Y% shops complete all tranches (likely higher due to behavioral effect)
```

---

## Code Structure

```python
# 1. Evidence
evidence = TierEvidenceInput(
    has_gst_filings=True,
    has_udyam_registration=False,
    has_prior_repayment_record=False,
    months_bank_history=18
)

# 2. Tier
tier = classifier.classify(evidence)  # TIER_2

# 3. ML Score
result = ensemble.score_shop(features)
# default_prob: 0.15, risk_band: "Moderate", safe_emi: ₹12k

# 4. Amount
amount_detail = calculator.calculate(
    evidence,
    capacity_model_emi=result.capacity.predicted_safe_emi,
    stock_limit=75000
)
# tier_cap: ₹300k, final_amount: ₹250k, tranched: False

# 5. Tranches (if Tier 3)
if amount_detail['tranched']:
    schedule = tranche_engine.calculate_tier3_schedule(amount_detail['final_amount'])
    # [40%, 30% @ 2 EMIs, 30% @ 4 EMIs]
```

---

## Testing Strategy

### Unit Tests
- `test_tier_classification()` - Each tier classifies correctly
- `test_amount_bounds()` - Min/max respected per tier
- `test_tranche_freeze()` - Freeze on 2 missed EMIs

### Integration Tests
- `test_scoring_pipeline()` - Evidence → tier → amount end-to-end
- `test_approval_by_tier()` - Count and amount by tier

### Evaluation Tests
- `test_claim_1_approval_rate()` - vs bureau baseline
- `test_claim_2_tranche_outcomes()` - vs single amount

---

## Backend Integration

**API endpoint (modified):**

```
POST /api/scoring/score

Request:
{
  "shop_id": "shop_001",
  "features": {...},  # 40 features
  "evidence": {       # NEW: tier evidence
    "has_gst_filings": true,
    "has_udyam_registration": false,
    "has_prior_repayment_record": false,
    "months_bank_history": 18
  },
  "stock_value": 75000
}

Response:
{
  "shop_id": "shop_001",
  "tier": 2,
  "default_probability": 0.15,
  "risk_band": "Moderate",
  "safe_emi": 12000,
  "loan_amount": 250000,
  "tranched": false,
  "reasons": [
    "Tier 2: GST filings available",
    "Capacity model: ₹288k",
    "Tier cap: ₹300k",
    "Stock limit: ₹75k (lowest)",
    "Final: ₹75k"
  ]
}
```

---

## Key Changes from Original Design

| Aspect | Before | After |
|---|---|---|
| **Primary decision** | Risk band + capacity | Tier (evidence-based) |
| **ML role** | Decides amount | Informs amount, not primary |
| **Amount rule** | Capacity model direct | min(capacity, tier_cap, stock_limit) |
| **Tranches** | Optional, final stage | Tier 3 mandatory, earlier |
| **Family size** | In scorecard | Only in household budget, EMI cap |
| **Evaluation** | Default rate, AUC | Approval by tier, tranche outcomes |

---

## Roadmap

### Immediate (this session)
1. ✓ Create `tier_rules.py` (classification, amount, tranches)
2. Create `scoring_pipeline.py` (end-to-end)
3. Create `evaluation_tiers.py` (claim testing)
4. Unit tests for tier rules
5. Integration test: evidence → amount

### Next (evaluation)
1. Run evaluation on Gen 2
2. Compare vs bureau baseline
3. Document results for design doc

### Final stage
1. Fairness audit (with/without family size)
2. Sign constraints
3. Reason stability
