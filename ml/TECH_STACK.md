# ML & AI Tech Stack Decisions

## Overview

| Task | Open-Source Option | Hosted/API Option | MVP Decision |
|---|---|---|---|
| **Photo understanding** (shop/shelf/bill) | Small open vision model, one-time download | Hosted vision model, call per photo | API for demo, local model later |
| **Bill & ledger reading** (Hindi, Kannada, English) | Tesseract OCR + language packs | Hosted vision model API | Manual entry in MVP, test both on 10 samples |
| **Photo authenticity** (metadata + tampering) | No reliable open model | Prompt-based API check | Use metadata (capture time, GPS) + API, label as weakest |
| **Sales & credit scoring** | scikit-learn (logistic regression, linear regression) | Not needed | ✓ Using scikit-learn |
| **Anomaly detection** (Isolation Forest, boosting) | scikit-learn, LightGBM | Not needed | ✓ Install locally with pip |
| **Reason writer** (plain language explanations) | Template-based | Hosted LLM API | Templates in MVP, add API in Final |

---

## Detailed Decisions by Component

### 1. Photo Understanding (Shop / Shelf / Bill)

**Purpose:** Classify uploaded photo type

**Options:**
- **Open-source:** Small vision model (e.g., MobileNetV3, DistilBERT + CLIP)
  - One-time download (~50-100 MB)
  - Fast inference locally
  - Accuracy: ~85-90%
  
- **Hosted API:** Cloud vision model
  - Per-call cost (e.g., Google Vision, AWS Rekognition)
  - Accuracy: ~95%+
  - Dependency on API availability

**MVP Decision:** 
- **Use API for demo** (faster to build, proven accuracy)
- **Download local model later** (reduce API calls, improve reliability)

**Implementation:**
```python
# MVP: API-based
def classify_photo_type(image_path: str) -> str:
    """Classify photo as 'shop_front', 'shelf', or 'bill'"""
    # Call hosted API
    client = vision.ImageAnnotatorClient()
    result = client.label_detection(image_path)
    # Parse and return type
    
# Final: Local model
def classify_photo_type_local(image_path: str) -> str:
    """Classify using downloaded CLIP model"""
    # Load model once at startup
    # Predict locally
```

---

### 2. Bill & Ledger Reading (Hindi, Kannada, English)

**Purpose:** Extract text from bills and handwritten ledgers

**Options:**
- **Open-source:** Tesseract OCR + language packs
  - Free, runs locally
  - Accuracy: 70-85% (varies by language)
  - Slow for handwriting
  
- **Hosted API:** Cloud OCR (e.g., Google Docs AI, Azure Form Recognizer)
  - Per-call cost
  - Accuracy: 90%+
  - Supports handwriting better

**MVP Decision:**
- **Manual entry** (users type supplier bills, amounts)
- **Test Tesseract vs API on 10 sample bills** before choosing
- **Benchmark:** Time, accuracy, cost-per-bill

**Evaluation Plan:**
```python
# 10 sample bills: mix of printed (invoice, receipt) and handwritten (ledger)
# For each:
#   - Time: tesseract vs API
#   - Accuracy: OCR'd vs manual ground truth
#   - Cost: if using API

# Decision rule:
#   If Tesseract MAE < 5%, use Tesseract (free, local)
#   Else use API (higher accuracy, worth the cost)
```

**Implementation (MVP):**
```python
# MVP: Manual entry
@app.post("/api/purchases/add")
def add_purchase(shop_id: str, supplier_id: str, amount: float, date: str):
    """User manually enters purchase details"""
    # Store in database
    # No OCR needed
    
# Test harness
def test_ocr_options(image_paths: list):
    """Compare Tesseract vs API on 10 sample bills"""
    results = []
    for img_path in image_paths:
        tesseract_result = tesseract.image_to_string(img_path, lang='hin+eng')
        api_result = call_vision_api(img_path)
        
        # Compare to ground truth
        results.append({
            'image': img_path,
            'tesseract_text': tesseract_result,
            'api_text': api_result,
            'accuracy': evaluate_accuracy(tesseract_result, api_result)
        })
    
    return results
```

---

### 3. Photo Authenticity Check

**Purpose:** Detect tampered or fake photos

**Options:**
- **Open-source:** No reliable model
  - Research exists but not production-ready
  - High false positive rate
  
- **Hosted API:** Cloud authenticity check
  - Metadata analysis + AI detection
  - Requires API call per photo
  - Cost per photo

**MVP Decision:**
- **Use metadata checks** (fast, free)
  - Capture time (must be recent)
  - GPS match (optional, if available)
  - Image properties (resolution, format)
  
- **Add prompt-based API check** (for demo)
  - Send image + metadata to LLM
  - Get simple pass/fail on authenticity
  
- **Label as weakest part** (accept lower confidence here)

**Implementation:**
```python
def check_photo_authenticity(image_path: str, expected_shop_location: dict = None) -> dict:
    """
    Check photo authenticity using metadata and optional API.
    
    Returns: {
        'authentic': bool,
        'score': 0-1,
        'metadata_pass': bool,
        'gps_match': bool or None,
        'api_check': bool or None,
        'reasons': [list of flags if inauthentic]
    }
    """
    
    metadata = extract_metadata(image_path)
    
    # Metadata checks (free, fast)
    reasons = []
    metadata_pass = True
    
    capture_time = metadata.get('datetime')
    if capture_time and (now - capture_time).days > 30:
        reasons.append('Photo older than 30 days')
        metadata_pass = False
    
    gps_match = None
    if expected_shop_location and metadata.get('gps'):
        distance = haversine_distance(
            metadata['gps'],
            expected_shop_location
        )
        gps_match = distance < 500  # 500m threshold
        if not gps_match:
            reasons.append(f'GPS distance: {distance}m (expected < 500m)')
    
    # Optional API check (for higher confidence)
    api_check = None
    if ENABLE_AUTHENTICITY_API:
        api_check = call_authenticity_api(image_path, metadata)
        if not api_check:
            reasons.append('Failed AI authenticity check')
    
    authentic = metadata_pass and (gps_match is None or gps_match) and (api_check is None or api_check)
    score = 0.7 if metadata_pass else 0.3
    if api_check:
        score = 0.9
    
    return {
        'authentic': authentic,
        'score': score,
        'metadata_pass': metadata_pass,
        'gps_match': gps_match,
        'api_check': api_check,
        'reasons': reasons
    }
```

---

### 4. Sales & Credit Scoring, Capacity Models

**Purpose:** Predict default probability and safe EMI

**Current Approach:** ✓ scikit-learn (logistic regression, linear regression)
- Installed and working
- Fast training (seconds on laptop)
- Easily explainable

**No changes needed.** Continue using:
- `train_models.py` → trains scorecard + capacity
- `scorer.py` → loads and uses models
- `tier_rules.py` → applies bounds and tier logic

---

### 5. Anomaly Detection (Optional)

**Purpose:** Detect round-trip transfers, sales inflation, etc.

**Options:**
- **Open-source:** Isolation Forest (scikit-learn), LightGBM
  - Already installable with pip
  - Fast inference
  - Good for unsupervised anomaly detection
  
**MVP Decision:** Keep simple
- Tier 2 MVP: Use hand-crafted rules (round-trip detection in code)
- Tier 3 Final: Add Isolation Forest if time permits

**Implementation:**
```python
# MVP: Rule-based
def detect_round_trip_transfers(transfers_df: pd.DataFrame) -> pd.Series:
    """Find A→B→A patterns (simple rule)"""
    suspicious = []
    for shop_id in transfers_df['shop_id'].unique():
        shop_transfers = transfers_df[transfers_df['shop_id'] == shop_id]
        # Check for circular patterns
        # ...
    return pd.Series(suspicious)

# Final: Isolation Forest
from sklearn.ensemble import IsolationForest

def detect_anomalies_isolation_forest(transfers_df: pd.DataFrame):
    """Detect outlier transfer patterns"""
    features = build_transfer_features(transfers_df)
    model = IsolationForest(contamination=0.05)
    anomalies = model.fit_predict(features) == -1
    return anomalies
```

---

### 6. Reason Writer (Plain-Language Explanations)

**Purpose:** Convert model outputs to human-readable reasons

**Current Approach:** Templates

**Options:**
- **MVP:** Hard-coded templates (fast, predictable)
  ```python
  reasons = {
      'low_cash_flow': "Low UPI inflow (₹{} avg) indicates limited turnover",
      'high_default_prob': "Higher default risk based on volatility in cash flow",
      'good_gst_match': "Sales and GST reconciliation strong (gap < 10%)"
  }
  ```
  
- **Final:** LLM API (more natural, flexible)
  ```python
  prompt = f"Explain why this shop has default probability {prob:.2%}"
  response = llm_api.generate(prompt)
  ```

**MVP Decision:**
- **Use templates** (reliable, no API dependency)
- **Add LLM in Final** (if time and budget permit)

---

## Cost Estimate (MVP)

| Component | Option | Cost/month | Notes |
|---|---|---|---|
| Photo understanding | API | $5-20 | ~100-500 photo classifications/month |
| Bill reading | Manual entry | $0 | No OCR needed |
| Authenticity | Metadata + optional API | $0-10 | Mostly free, optional API calls |
| Scoring models | scikit-learn (local) | $0 | Free, runs on laptop |
| Anomaly detection | Rules | $0 | No ML needed |
| Reason writer | Templates | $0 | Hard-coded |
| **Total** | | **$5-30/month** | Minimal cost |

---

## Implementation Roadmap

### This Sprint (MVP)
1. ✓ Scoring models (scorecard, capacity)
2. ✓ Tier rules (classification, amount, tranches)
3. ✓ Tier pipeline (end-to-end scoring)
4. **Photo understanding:** Stub for API calls (don't implement yet)
5. **Bill reading:** Manual entry form only
6. **Reason writer:** Use templates
7. **Authenticity:** Use metadata only (skip API)

### Next Sprint (Final)
1. Integrate photo understanding API
2. Test Tesseract vs API on sample bills
3. Add authenticity API check
4. Add LLM-based reason writer
5. Optional: Local vision model download

### Testing Before Choosing
```python
# Before committing to OCR API, run:
test_bills = ['bill1.jpg', 'bill2.jpg', ..., 'bill10.jpg']
results = test_ocr_options(test_bills)

# Compare:
# - Time per bill (Tesseract vs API)
# - Accuracy (vs manual ground truth)
# - Cost-per-bill (if using API)
# - Dependency risk (API availability)

# Decision: Pick the winner
```

---

## Backend Integration Points

The ML component provides these APIs to the backend:

```python
# 1. Scoring pipeline (ready now)
POST /api/scoring/score
→ Returns: tier, scores, amount, tranches

# 2. Photo classification (stub, calls external API)
POST /api/photo/classify
→ Returns: photo_type (shop_front, shelf, bill)

# 3. Photo authenticity (metadata + optional API)
POST /api/photo/check-authenticity
→ Returns: authentic, score, metadata_pass, gps_match

# 4. Bill OCR (manual entry in MVP)
POST /api/purchases/add
→ User provides: supplier_id, amount, date

# 5. Reasons (template-based)
GET /api/reasons/{shop_id}
→ Returns: list of plain-language reasons
```

---

## Files to Create/Update

### Already Done ✓
- `train_models.py` - Train scorecard + capacity
- `scorer.py` - Load and use models
- `tier_rules.py` - Tier classification and amount
- `scoring_pipeline.py` - End-to-end pipeline

### TODO (Next)
- `photo_handler.py` - Photo classification stub
- `bill_reader.py` - OCR testing harness
- `reason_generator.py` - Template-based reasons
- `authenticity_checker.py` - Metadata + optional API
- Tests for each module

### Stretch (Final)
- `vision_models.py` - Download and cache local models
- `llm_reasons.py` - LLM API for reasons
- `anomaly_detector.py` - Isolation Forest implementation
