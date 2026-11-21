# ML Implementation Checklist

## ✅ Completed (MVP Stage 2)

### Models & Training
- [x] Credibility scorecard (logistic regression)
  - Train AUC: 0.6163
  - Val AUC: 0.5312
  - Test AUC: 0.6102
  
- [x] Repayment capacity model (linear regression)
  - Train R²: 0.8200
  - Val R²: 0.7899
  - Test R²: 0.8302
  - MAE: ₹703, median error: 1.4%

### Architecture & Pipelines
- [x] Tiered product design (3 tiers based on evidence)
- [x] Tier classification rules
- [x] Amount calculation (min of capacity, tier cap, stock limit)
- [x] Tranche engine (40/30/30 split, freeze on 2 missed EMIs)
- [x] End-to-end scoring pipeline

### Code Modules
- [x] `train_models.py` - Training pipeline
- [x] `scorer.py` - Model loading and scoring (`ModelEnsemble` class)
- [x] `tier_rules.py` - Tier classification and amount rules
- [x] `scoring_pipeline.py` - End-to-end pipeline (`ScoringPipeline` class)
- [x] `reason_generator.py` - Template-based reason generation

### Documentation
- [x] `MODEL_TRAINING.md` - Original tiered design overview
- [x] `TIERED_DESIGN.md` - Detailed architecture and evaluation plan
- [x] `TECH_STACK.md` - Tech decisions and roadmap
- [x] `IMPLEMENTATION_CHECKLIST.md` - This file

### Data & Artifacts
- [x] Synthetic data generators (Gen 1: 5,000 shops, Gen 2: 1,500 shops)
- [x] 40 features (cash flow, GST, reconciliation, stock, vintage, anomalies)
- [x] Saved models: scorecard.pkl, capacity_model.pkl, scalers, metadata.json

---

## ⏳ Pending (Still TODO)

### Backend Integration
- [ ] API endpoint: `POST /api/scoring/score`
  - Input: shop_id, features, evidence, stock_value
  - Output: tier, scores, amount, tranches, reasons
  
- [ ] Response format validation
- [ ] Error handling (missing features, invalid evidence)
- [ ] Logging and monitoring

### Evaluation Scripts
- [ ] Claim 1: Approval rate by tier vs bureau baseline
  - Gen 2 approval counts by tier
  - Amount approved by tier
  - Comparison vs bureau (known from doc)
  
- [ ] Claim 2: Tranche outcomes vs single amount
  - Simulate Tier 3 repayment sequences
  - Compare completion rates: tranched vs single

### Testing
- [ ] Unit tests for tier classification
  - Each tier classifies correctly on edge cases
  - Tier boundaries work properly
  
- [ ] Unit tests for amount calculation
  - min() logic works
  - Bounds respected (min/max per tier)
  
- [ ] Unit tests for tranche engine
  - Schedule calculated correctly
  - Freeze rule works (2 missed EMIs)
  
- [ ] Integration tests
  - End-to-end: evidence → tier → amount
  - Batch scoring (multiple shops)
  
- [ ] Reason generation tests
  - Each reason template produces valid output
  - Reasons make sense for edge cases

### Fairness & Constraints
- [ ] Fairness audit: approval rates with/without family size
- [ ] Sign-constraint tests
  - More debt → scorecard should not increase
  - Fewer verified records → score should not increase
  
- [ ] Calibration check
  - Predicted vs actual default rate by risk band
  - Capacity model: predicted vs actual EMI performance

### Stretch Goals (Final Stage)
- [ ] Photo classification API stub (MVP → local model)
- [ ] Bill OCR testing harness (compare Tesseract vs API on 10 samples)
- [ ] Photo authenticity check (metadata → +API)
- [ ] LLM-based reason writer (templates → +LLM)
- [ ] Anomaly detection enhancement (rules → Isolation Forest)

---

## How to Use

### 1. Train Models (One-time)
```bash
cd ml
python train_models.py
```
Output: `models/` with 5 files (scorecard, capacity, scalers, metadata)

### 2. Score Individual Shops
```python
from scoring_pipeline import ScoringPipeline
from tier_rules import TierEvidenceInput

pipeline = ScoringPipeline('models')

evidence = TierEvidenceInput(
    has_gst_filings=True,
    has_udyam_registration=False,
    has_prior_repayment_record=False,
    months_bank_history=18
)

decision = pipeline.score(
    shop_id="shop_001",
    features={...},  # 40 features
    evidence=evidence,
    stock_value=75000
)

print(decision.to_dict())
```

### 3. Score Batch
```python
batch_results = pipeline.score_batch(df)
# Returns DataFrame with: tier, scores, amount, tranches
```

### 4. Generate Reasons
```python
from reason_generator import ReasonGenerator

generator = ReasonGenerator()
reasons = generator.generate_reasons(decision.to_dict())

for reason in reasons:
    print(f"• {reason}")
```

### 5. Demo Scripts
```bash
# Scoring pipeline demo
cd ml
python scoring_pipeline.py

# Reason generation demo
python reason_generator.py

# Tier rules demo
python tier_rules.py
```

---

## Backend Integration (Next Sprint)

### Add to `be/api/main.py`:

```python
from ml.scoring_pipeline import ScoringPipeline
from ml.tier_rules import TierEvidenceInput
from ml.reason_generator import ReasonGenerator

# Initialize (at startup)
pipeline = ScoringPipeline('ml/models')
reason_gen = ReasonGenerator()

@app.post("/api/scoring/score")
def score_shop(request: ScoringRequest):
    """Score a shop and return tier, amount, and reasons."""
    
    # Parse evidence
    evidence = TierEvidenceInput(
        has_gst_filings=request.has_gst_filings,
        has_udyam_registration=request.has_udyam_registration,
        has_prior_repayment_record=request.has_prior_repayment_record,
        months_bank_history=request.months_bank_history
    )
    
    # Build features from request
    features = {
        'upi_inflow_mean': request.upi_inflow_mean,
        # ... all 40 features
    }
    
    # Score
    decision = pipeline.score(
        shop_id=request.shop_id,
        features=features,
        evidence=evidence,
        stock_value=request.stock_value
    )
    
    return decision.to_dict()
```

### Request Model:

```python
class ScoringRequest(BaseModel):
    shop_id: str
    
    # Evidence
    has_gst_filings: bool
    has_udyam_registration: bool
    has_prior_repayment_record: bool
    months_bank_history: int
    
    # Stock
    stock_value: float
    
    # 40 features (from feature_builder)
    upi_inflow_mean: float
    upi_inflow_std: float
    cash_deposits_mean: float
    # ... (all features)
```

---

## Evaluation (To Run on Gen 2)

### Claim 1: Approval Rate by Tier

```python
# Load test data
features_test = pd.read_csv('ml/data/features_gen2.csv')
labels_test = pd.read_csv('ml/data/labels_gen2.csv')
shops_test = pd.read_csv('ml/data/shops_gen2.csv')

# Score all shops
results = []
for idx, row in features_test.iterrows():
    decision = pipeline.score(...)
    results.append(decision.to_dict())

results_df = pd.DataFrame(results)

# By tier
print("APPROVAL RATE BY TIER")
for tier in [1, 2, 3]:
    tier_data = results_df[results_df['tier'] == tier]
    count = len(tier_data)
    amount = tier_data['final_amount'].sum()
    print(f"Tier {tier}: {count} approved, ₹{amount:,.0f} total")

# Compare vs bureau baseline (from doc):
# Bureau: Tier 1: 50, ₹1.5M; Tier 2: 200, ₹35M; Tier 3: 80, ₹50M
```

### Claim 2: Tranche Outcomes

```python
# Simulate EMI payment for Tier 3 shops
tier3_shops = results_df[results_df['tier'] == 3]

for shop in tier3_shops.itertuples():
    # Get historical EMI payment pattern
    payment_history = get_shop_payment_history(shop.shop_id)
    
    # Check if completed all tranches
    completed_all_tranches = check_tranche_completion(
        shop.tranche_schedule,
        payment_history
    )
    
    # Compare vs single-amount scenario
    # (would all EMIs have been paid with single amount?)
```

---

## Files Reference

| File | Purpose | Status |
|---|---|---|
| `train_models.py` | Train models on Gen 1, test on Gen 2 | ✓ Done |
| `scorer.py` | Load models and score shops | ✓ Done |
| `tier_rules.py` | Tier classification and amount rules | ✓ Done |
| `scoring_pipeline.py` | End-to-end pipeline | ✓ Done |
| `reason_generator.py` | Generate reasons | ✓ Done |
| `MODEL_TRAINING.md` | Tiered design overview | ✓ Done |
| `TIERED_DESIGN.md` | Detailed architecture | ✓ Done |
| `TECH_STACK.md` | Tech decisions and roadmap | ✓ Done |
| `models/scorecard.pkl` | Trained scorecard | ✓ Done |
| `models/capacity_model.pkl` | Trained capacity model | ✓ Done |
| `ml/data/features_gen*.csv` | Generated datasets | ✓ Done |

---

## Performance Summary

### Scorecard Performance
- **Train AUC:** 0.6163 (modest but consistent)
- **Test AUC:** 0.6102 (generalizes well)
- **Interpretation:** Use as risk signal, not sole decision

### Capacity Performance
- **Train R²:** 0.8200 (strong on synthetic)
- **Test R²:** 0.8302 (very strong generalization)
- **MAE:** ₹703, median error 1.4%
- **Interpretation:** Reliable EMI predictor on synthetic; real performance TBD

### Tier Distribution (Gen 2)
- **Tier 1:** ~200 shops (13%)
- **Tier 2:** ~800 shops (53%)
- **Tier 3:** ~500 shops (34%)

---

## Known Limitations

1. **AUC 0.61:** Scorecard is modest; honest about this
2. **Synthetic data:** R² of 0.83 is partly by construction
3. **No OCR:** Manual entry required in MVP
4. **No local models:** Using hosted APIs for photo classification
5. **Family size excluded:** Won't appear in scorecard (fairness by design)
6. **Single chain:** Fixed pipeline, not agentic

---

## Next Steps

1. **Backend integration** - Implement `/api/scoring/score` endpoint
2. **Run evaluation** - Measure Claim 1 and Claim 2 on Gen 2
3. **Write tests** - Unit and integration tests for all tiers and rules
4. **Documentation** - Update design doc with measured results
5. **Demo** - Run end-to-end through frontend (if time permits)
