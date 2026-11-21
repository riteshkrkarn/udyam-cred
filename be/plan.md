# UdyamCred Backend — Implementation Plan

## Stage 1 (Complete ✅)

Stage 1 delivered the foundation for UdyamCred: a FastAPI backend that, for a
synthetic shop, decides whether its declared sales match its stock given a
category margin, and shows the verdict. The headline Stage-1 claim — *two shops
with the same UPI inflow get different verdicts* — is enforced and tested.

**Status:** ✅ 95 tests passing, 90% coverage, all endpoints working

## Stage 2 (In Progress 🚀)

Stage 2 extends the backend with ML integration, risk scoring, multi-criteria
decision logic, batch operations, and a shop management API. The system moves
from verdict-only to a full decision engine with risk stratification.

### Phase 2 Goals

1. **ML Model Integration** - Import trained ML models (or mock placeholders) to score shop risk
2. **Enhanced Reconciliation** - Combine rule-based logic with ML scoring (hybrid decision)
3. **Risk Stratification** - Assign risk levels (LOW/MEDIUM/HIGH) based on multiple signals
4. **Batch Operations** - `/reconcile/batch` endpoint to process multiple shops
5. **Shop Management API** - CRUD endpoints for shop data persistence
6. **Decision History** - Track reconciliation decisions per shop (audit trail)
7. **Enhanced Auth** - Role-based access control (RBAC) for different user types
8. **Performance** - Caching, indexing for high-volume queries

### Phase 2 Deliverables

#### A. ML Integration & Hybrid Scoring
- Import ML generator/feature builder
- Add ML risk score to `/reconcile` response
- Combine rule verdict + ML score → final decision
- Schema: add `ml_risk_score`, `final_decision`, `confidence_level`

#### B. Shop Management Endpoints
```
POST   /shops              # Create shop record
GET    /shops/{shop_id}    # Fetch shop details
PUT    /shops/{shop_id}    # Update shop data
DELETE /shops/{shop_id}    # Archive shop
GET    /shops              # List shops (paginated)
```

#### C. Batch Reconciliation
```
POST /reconcile/batch      # Process 10-1000 shops in one request
GET  /reconcile/results    # Fetch past reconciliation results (paginated)
```

#### D. Decision History & Audit Trail
- New table: `ReconciliationHistory` (tracks all decisions per shop)
- New table: `AuditLog` (user actions + reasoning)
- Endpoint: `GET /shops/{shop_id}/history` - show all past verdicts

#### E. Risk Dashboard Data
```
GET /analytics/summary     # Overall verdict breakdown
GET /analytics/by-category # Verdicts grouped by shop category
GET /analytics/top-flagged # Shops with highest risk scores
GET /analytics/trends      # Verdict trends over time
```

#### F. Role-Based Access Control
- Enforce user roles: `borrower`, `officer`, `approver`, `auditor`
- Different roles see different data
- Approvers can override verdicts
- Auditors get full read-only access

#### G. Monitoring & Performance
- Add request/response logging
- Track API latency
- Cache frequently accessed policies/categories
- Index shop_id, gstin, category in DB

---

## Layout

```
be/
  app/
    __init__.py
    config.py          # settings from env/.env (lru_cache singleton)
    database.py        # SQLAlchemy engine, SessionLocal, Base, init_db, get_db
    models.py          # ORM: User, Shop, ReconciliationResult, RefreshToken
    utils.py           # utcnow_naive() helper (naive UTC for SQLite storage)
    policy.py          # Policy / CategoryPolicy loader for config/policy.yaml
    gstin.py           # GSTIN validator (length, state code, checksum)
    reconciliation.py  # reconcile() + reconcile_many()
    auth.py            # bcrypt hashing, JWT access tokens, refresh hashing/expiry
    schemas.py         # pydantic request/response models
  synth/
    generator.py       # SyntheticDataGenerator (deterministic, scenario-based)
  config/
    policy.yaml        # 8 leaf shop categories + kirana_overall aggregate, margins
  scripts/
    seed.py            # init_db_tables, create_test_users, load_synthetic_data, CLI
  tests/
    conftest.py        # shared fixtures (policy, generator, engine, db_session, client)
    test_gstin.py
    test_generator.py
    test_reconciliation.py
    test_seed.py
    test_golden.py
    test_auth.py
    golden_expected.csv
  data/synthetic/      # generated shop CSVs land here (gitignored)
  requirements.txt
  .env.example
  .gitignore
  pytest.ini
  main.py              # FastAPI app: health, auth, /reconcile
  plan.md
```

## Domain model and reconciliation

A shop carries: `gstin`, `shop_category` (one of 8 leaf categories),
`purchases` (cost of goods sold), `gst_turnover` (declared sales), and
`upi_turnover` (digital receipts).

The spec's inverse formula (margin on selling price) is implemented exactly:

```
expected_sales = goods_sold / (1 + margin)
```

For a category margin range `[margin_low, margin_high]` the expected-sales band
is:

```
expected_sales_high = goods_sold / (1 + margin_low)   # lower margin -> higher expected
expected_sales_low  = goods_sold / (1 + margin_high)  # higher margin -> lower expected
```

A tolerance (`policy.tolerance`, default ±0.5%) is applied to both ends so
point-valued categories (e.g. `kirana_with_inventory = 15%`) behave as a thin
band rather than a degenerate point.

`reconcile(shop, policy)` returns a verdict:

| verdict   | when                                                                 |
|-----------|----------------------------------------------------------------------|
| rejected  | GSTIN fails format/state/checksum validation                         |
| flagged   | UPI receipts exceed declared GST sales, or declared sales fall outside the expected band (suppression if below, overstatement if above) |
| approved  | declared sales sit inside the expected margin band                   |

## GSTIN validation

15-char structure: state code (01–38) + 5 letters + 4 digits + 1 letter + 1
alphanumeric entity code + `Z` + 1 alphanumeric check digit.

Checksum: map each of the first 14 chars to 0–35 (0-9 → 0-9, A-Z → 10-35), apply
alternating weights 1,2,1,2,… starting at 1, add `(product // 36) + (product % 36)`
per char, then `check = (36 - sum % 36) % 36`. `is_valid_gstin` never raises;
`validate_gstin` raises `GSTINError`. `make_valid_gstin(prefix14)` appends the
correct check digit (used by tests and the generator).

## Policy (config/policy.yaml)

Eight leaf shop categories under `shop_categories`, plus `kirana_overall`
(8–10%) under `aggregates` as the parent reference band. The 10 listed margin
figures map to 8 leaf categories because `kirana_overall` is the aggregate.

| category                  | margin      |
|---------------------------|-------------|
| kirana_with_inventory     | 15%         |
| kirana_without_inventory  | 10%         |
| branded_staples           | 3–9%        |
| packaged_fmcg             | 7–14%       |
| beverages_impulse         | 10–18%      |
| personal_care             | 12–20%      |
| general_merchandise       | 14–25%      |
| loose_goods               | 14–30%      |

## Synthetic generator

`SyntheticDataGenerator(policy, seed)` is fully deterministic for a given seed
(seeded `random.Random`). Each shop's *verdict is fixed by construction*: the
relationship between `purchases`, `gst_turnover` and `upi_turnover` is chosen
per scenario, so verdicts are meaningful rather than accidental. A small seeded
jitter on `purchases`/`inventory` provides variety without changing verdicts.

Scenarios repeat every 10 shops. The first ten (seed 42) are the golden set:

| shop | scenario            | category                 | verdict  |
|------|---------------------|--------------------------|----------|
| 0    | approved            | kirana_without_inventory | approved |
| 1    | suppression        | loose_goods              | flagged  |
| 2    | invalid_gstin      | packaged_fmcg            | rejected |
| 3    | approved           | branded_staples          | approved |
| 4    | upi_exceeds_gst    | beverages_impulse        | flagged  |
| 5    | approved           | personal_care            | approved |
| 6    | suppression         | general_merchandise      | flagged  |
| 7    | approved           | packaged_fmcg            | approved |
| 8    | suppression         | kirana_with_inventory    | flagged  |
| 9    | approved           | loose_goods              | approved |

Verdict mix: 5 approved, 4 flagged, 1 rejected.

**Pair case.** Shops 0 and 1 are explicitly given the same UPI inflow
(400,000). Shop 0's declared sales sit at its expected band midpoint (margin
10%, purchases ≈1.0m → expected ≈0.91m) so it is approved. Shop 1 has higher
purchases and a higher-margin category (loose_goods, 14–30%) so its expected
band is well above its declared sales → flagged. Same UPI, different verdicts,
because the verdict depends on the stock/margin reconciliation, not UPI alone.

## Auth (JWT, refresh rotation, remember-me)

- **Access token:** signed JWT (HS256), 15-minute lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Refresh token:** opaque `secrets.token_urlsafe`, stored **hashed** (sha256)
  in `refresh_tokens`. Rotation on `POST /auth/refresh` revokes the old token
  (`revoked=True`, `replaced_by` set) and issues a new one — single-use.
- **Remember me:** refresh lifetime is 1 day with `remember_me=true`, else 1 hour
  (`REMEMBER_ME_EXPIRE_HOURS` / `REFRESH_TOKEN_EXPIRE_HOURS`).
- Passwords hashed with bcrypt; the raw value is never stored.

Endpoints: `GET /health`, `POST /auth/register`, `POST /auth/login`,
`POST /auth/refresh`, `POST /auth/logout`, `POST /reconcile` (auth-protected),
`GET /shops/me`.

## Running

```bash
# from be/
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# set up database, test users, and 10 synthetic shops (seed 42)
python scripts/seed.py                     # also: --shops N --seed S --csv path.csv
python scripts/seed.py --init-only          # tables only

# serve
uvicorn main:app --reload

# tests with coverage
python -m pytest tests --cov=app --cov=synth --cov=scripts --cov=main --cov-report=term-missing
```

## Test results

95 tests pass, 90% coverage. Suites:

- `test_gstin.py` — valid GSTINs (7), invalid cases (wrong length, bad state,
  bad pattern, bad checksum), checksum internals.
- `test_generator.py` — determinism (same seed equal, different seed different),
  shape, the pair case, scenario/verdict composition.
- `test_reconciliation.py` — approved/rejected/flagged branches, inverse-formula
  math, band ordering, ORM-object input, unknown-category error.
- `test_seed.py` — init_db tables, idempotent users, load_synthetic_data counts,
  verdict mix, replacement on reload, pair case in DB, CSV export.
- `test_golden.py` — seed-42 dataset reproduces `golden_expected.csv` (shop_id,
  category, gstin_valid, verdict) and the pair case.
- `test_auth.py` — register/login, protected `/reconcile`, refresh rotation
  (old token revoked, single-use), logout.

## Notes and assumptions

- The spec's formula `expected_sales = goods_sold / (1 + margin)` is implemented
  literally. With a positive margin this makes `expected_sales < goods_sold`;
  the dataset and verdicts are self-consistent with that formula. `goods_sold`
  is the shop's purchases (cost of goods); `expected_sales` is the declared
  sales band implied by the category margin.
- `kirana_overall` is modelled as an aggregate, not a leaf shop category, so the
  "8 shop categories" and the 9 listed margin figures are consistent.
- Test DBs use in-memory SQLite (`StaticPool`, single connection) so API writes
  are visible to direct queries in the same test.
- `data/synthetic/*.csv` is gitignored (generated); `tests/golden_expected.csv`
  is the committed regression lock.

---

## Stage 2 Implementation Plan (Detailed)

### Phase 2A: ML Integration (Week 1)

#### 1. Create ML Scoring Module
**File:** `app/ml_scorer.py`

```python
class MLScorer:
    """Wrapper for ML model predictions"""
    
    def __init__(self, model_path=None):
        # Load trained model or use mock
        pass
    
    def score_shop(self, shop_dict) -> Dict:
        """
        Input: shop data (purchases, gst, upi, category, etc)
        Output: {
            "ml_risk_score": 0.0-1.0,
            "ml_prediction": "safe" | "risky",
            "model_version": "v1.0"
        }
        """
        pass
    
    def score_batch(self, shops: List[Dict]) -> List[Dict]:
        """Batch scoring for performance"""
        pass
```

#### 2. Update Reconciliation Logic
**File:** `app/reconciliation.py` (extend)

```python
def reconcile_with_ml(shop, policy, ml_scorer) -> dict:
    """
    Combine rule-based verdict + ML score
    
    Output schema:
    {
        ...existing fields...,
        "ml_risk_score": float (0-1),
        "ml_prediction": "safe" | "risky",
        "verdict": "approved" | "flagged" | "rejected",
        "final_risk_level": "LOW" | "MEDIUM" | "HIGH",
        "confidence": float (0-1),
        "recommendation": str
    }
    """
    # 1. Get rule-based verdict
    rule_result = reconcile(shop, policy)
    
    # 2. Get ML score
    ml_result = ml_scorer.score_shop(shop)
    
    # 3. Combine logic:
    #    - rejected always stays rejected
    #    - if rule=approved but ML_risk > 0.7 → MEDIUM risk
    #    - if rule=flagged and ML_risk > 0.8 → HIGH risk
    #    - else → LOW risk
    
    return combined_result
```

#### 3. Update Schemas
**File:** `app/schemas.py` (extend)

```python
class ReconciliationOut(BaseModel):
    # Existing fields...
    shop_id: str
    verdict: str  # approved, flagged, rejected
    reason: str
    
    # NEW fields
    ml_risk_score: float
    ml_prediction: str
    final_risk_level: str  # LOW, MEDIUM, HIGH
    confidence: float
    recommendation: str
```

#### 4. Update Main Endpoint
**File:** `main.py`

```python
@app.post("/reconcile", response_model=ReconciliationOut)
def reconcile_endpoint(
    shop_in: ShopIn,
    current_user: User = Depends(get_current_user),
    ml_scorer: MLScorer = Depends(get_ml_scorer),
) -> ReconciliationOut:
    """Run stock reconciliation with ML scoring"""
    policy = load_policy()
    result = reconcile_with_ml(shop_in.model_dump(), policy, ml_scorer)
    
    # Save to DB for audit
    save_reconciliation_result(current_user.id, result)
    
    return ReconciliationOut(**result)
```

**Tests:**
- `test_ml_scorer.py` - mock ML scorer with deterministic outputs
- `test_hybrid_reconciliation.py` - rule + ML combinations
- `test_reconciliation_output.py` - verify new schema fields

---

### Phase 2B: Shop Management API (Week 1-2)

#### 1. Extend Models
**File:** `app/models.py` (add)

```python
class Shop(Base):
    __tablename__ = "shops"
    
    id = Column(Integer, primary_key=True)
    shop_id = Column(String, unique=True, index=True)  # User-facing ID
    user_id = Column(Integer, ForeignKey("users.id"))
    gstin = Column(String, index=True)
    shop_category = Column(String)
    shop_name = Column(String)
    city = Column(String)
    shop_owner = Column(String)
    
    # Financial data
    purchases = Column(Float)
    gst_turnover = Column(Float)
    upi_turnover = Column(Float)
    
    # Status
    status = Column(String, default="active")  # active, archived
    last_verified = Column(DateTime, default=utcnow_naive)
    
    # Relationships
    user = relationship("User", back_populates="shops")
    reconciliation_results = relationship("ReconciliationResult")

class ReconciliationHistory(Base):
    __tablename__ = "reconciliation_history"
    
    id = Column(Integer, primary_key=True)
    shop_id = Column(String, ForeignKey("shops.shop_id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    verdict = Column(String)
    ml_score = Column(Float)
    rule_reason = Column(String)
    timestamp = Column(DateTime, default=utcnow_naive, index=True)
    notes = Column(String, nullable=True)
```

#### 2. Create Shop CRUD Endpoints
**File:** `app/shop_routes.py` (new)

```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/shops", tags=["shops"])

@router.post("", response_model=ShopOut, status_code=201)
def create_shop(
    shop: ShopIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOut:
    """Create a new shop record"""
    if db.query(Shop).filter_by(shop_id=shop.shop_id).first():
        raise HTTPException(status_code=409, detail="shop_id already exists")
    
    shop_obj = Shop(**shop.dict(), user_id=current_user.id)
    db.add(shop_obj)
    db.commit()
    db.refresh(shop_obj)
    return ShopOut.from_orm(shop_obj)

@router.get("/{shop_id}", response_model=ShopOut)
def get_shop(
    shop_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOut:
    """Fetch a shop by ID (only owner can view)"""
    shop = db.query(Shop).filter_by(shop_id=shop_id).first()
    if not shop or shop.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="shop not found")
    return ShopOut.from_orm(shop)

@router.put("/{shop_id}", response_model=ShopOut)
def update_shop(
    shop_id: str,
    update: ShopUpdateIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShopOut:
    """Update shop data"""
    shop = db.query(Shop).filter_by(shop_id=shop_id).first()
    if not shop or shop.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="shop not found")
    
    for field, value in update.dict(exclude_unset=True).items():
        setattr(shop, field, value)
    
    db.commit()
    db.refresh(shop)
    return ShopOut.from_orm(shop)

@router.delete("/{shop_id}", status_code=204)
def archive_shop(
    shop_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Archive a shop (soft delete)"""
    shop = db.query(Shop).filter_by(shop_id=shop_id).first()
    if not shop or shop.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="shop not found")
    
    shop.status = "archived"
    db.commit()

@router.get("", response_model=List[ShopOut])
def list_shops(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ShopOut]:
    """List all shops for current user (paginated)"""
    shops = db.query(Shop)\
        .filter_by(user_id=current_user.id, status="active")\
        .offset(skip)\
        .limit(limit)\
        .all()
    return [ShopOut.from_orm(s) for s in shops]
```

#### 3. Update Main App
**File:** `main.py` (add)

```python
from app.shop_routes import router as shop_router

app.include_router(shop_router)
```

**Tests:**
- `test_shop_crud.py` - create, read, update, delete, list
- `test_shop_permissions.py` - users can only see own shops
- `test_shop_validation.py` - invalid GSTIN, duplicate shop_id, etc

---

### Phase 2C: Batch Reconciliation (Week 2)

#### 1. Batch Endpoint
**File:** `main.py` (add)

```python
class ReconcileBatchIn(BaseModel):
    shops: List[ShopIn]
    max_workers: int = 4  # Parallel processing

class ReconcileBatchOut(BaseModel):
    total: int
    approved: int
    flagged: int
    rejected: int
    results: List[ReconciliationOut]
    processing_time_ms: float

@app.post("/reconcile/batch", response_model=ReconcileBatchOut)
def reconcile_batch(
    batch: ReconcileBatchIn,
    current_user: User = Depends(get_current_user),
):
    """Process multiple shops in parallel"""
    from concurrent.futures import ThreadPoolExecutor
    import time
    
    start = time.time()
    policy = load_policy()
    ml_scorer = get_ml_scorer()
    
    results = []
    with ThreadPoolExecutor(max_workers=batch.max_workers) as executor:
        futures = [
            executor.submit(reconcile_with_ml, shop, policy, ml_scorer)
            for shop in batch.shops
        ]
        results = [f.result() for f in futures]
    
    processing_time = (time.time() - start) * 1000
    
    verdicts = [r["verdict"] for r in results]
    return ReconcileBatchOut(
        total=len(results),
        approved=verdicts.count("approved"),
        flagged=verdicts.count("flagged"),
        rejected=verdicts.count("rejected"),
        results=results,
        processing_time_ms=processing_time,
    )
```

#### 2. Results History Endpoint
```python
@app.get("/reconcile/results", response_model=List[ReconciliationHistoryOut])
def get_reconciliation_history(
    shop_id: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch past reconciliation results"""
    query = db.query(ReconciliationHistory)\
        .filter_by(user_id=current_user.id)
    
    if shop_id:
        query = query.filter_by(shop_id=shop_id)
    
    results = query\
        .order_by(ReconciliationHistory.timestamp.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return results
```

**Tests:**
- `test_batch_reconciliation.py` - 100+ shops, verify counts
- `test_batch_performance.py` - benchmark parallel processing
- `test_reconciliation_history.py` - history persistence

---

### Phase 2D: Analytics Dashboard (Week 2-3)

#### Analytics Endpoints
**File:** `app/analytics_routes.py` (new)

```python
@router.get("/summary")
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Overall verdict breakdown"""
    results = db.query(ReconciliationHistory)\
        .filter_by(user_id=current_user.id)\
        .all()
    
    verdicts = [r.verdict for r in results]
    return {
        "total_reconciliations": len(results),
        "approved": verdicts.count("approved"),
        "flagged": verdicts.count("flagged"),
        "rejected": verdicts.count("rejected"),
        "approval_rate": verdicts.count("approved") / len(results) if results else 0,
    }

@router.get("/by-category")
def get_by_category(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verdicts grouped by shop category"""
    from sqlalchemy import func
    
    results = db.query(
        Shop.shop_category,
        ReconciliationHistory.verdict,
        func.count().label("count")
    ).join(ReconciliationHistory)\
     .filter(Shop.user_id == current_user.id)\
     .group_by(Shop.shop_category, ReconciliationHistory.verdict)\
     .all()
    
    return results

@router.get("/top-flagged")
def get_top_flagged(limit: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Shops with highest risk scores"""
    flagged = db.query(ReconciliationHistory)\
        .filter_by(user_id=current_user.id, verdict="flagged")\
        .order_by(ReconciliationHistory.ml_score.desc())\
        .limit(limit)\
        .all()
    return flagged
```

---

### Phase 2E: Role-Based Access Control (Week 3)

#### Permissions Decorator
**File:** `app/permissions.py` (new)

```python
from functools import wraps

ROLE_PERMISSIONS = {
    "borrower": ["view_own_shops", "submit_reconciliation"],
    "officer": ["view_all_shops", "submit_reconciliation", "view_analytics"],
    "approver": ["view_all_shops", "approve_verdict", "override_decision"],
    "auditor": ["view_all_shops", "view_analytics", "view_history"],
}

def require_role(*roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(current_user: User = Depends(get_current_user), *args, **kwargs):
            if current_user.role not in roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(current_user=current_user, *args, **kwargs)
        return wrapper
    return decorator
```

#### Usage in Endpoints
```python
@app.get("/analytics/summary")
@require_role("officer", "approver", "auditor")
def get_analytics_summary(current_user: User = Depends(get_current_user)):
    """Only officers, approvers, and auditors can view"""
    pass
```

---

### Phase 2F: Database Migrations & Indexing

#### Create Migrations
```bash
# Using Alembic (recommended for production)
alembic init migrations
alembic revision --autogenerate -m "Add shop and history tables"
alembic upgrade head
```

#### Key Indexes
```sql
CREATE INDEX idx_shop_user_id ON shops(user_id);
CREATE INDEX idx_shop_gstin ON shops(gstin);
CREATE INDEX idx_reconciliation_user_ts ON reconciliation_history(user_id, timestamp DESC);
CREATE INDEX idx_reconciliation_shop_id ON reconciliation_history(shop_id);
```

---

### Phase 2G: Testing Strategy

#### New Test Files
- `test_ml_scorer.py` - ML model integration
- `test_hybrid_reconciliation.py` - rule + ML combinations
- `test_shop_crud.py` - shop management endpoints
- `test_batch_reconciliation.py` - batch processing
- `test_analytics.py` - dashboard endpoints
- `test_rbac.py` - role-based access control
- `test_performance.py` - latency benchmarks

#### Test Coverage Goal
- **Minimum 85% coverage** on new code
- **100% on critical paths** (ML scoring, batch processing)
- Load test: 1000 shops/minute

---

## Phase 2 Timeline

| Week | Deliverable | Status |
|------|-------------|--------|
| W1 | A. ML Integration | 🔄 Starting |
| W1-2 | B. Shop Management API | 🔄 Starting |
| W2 | C. Batch Operations | ⏳ Planned |
| W2-3 | D. Analytics Dashboard | ⏳ Planned |
| W3 | E. RBAC | ⏳ Planned |
| W3 | F. Migrations | ⏳ Planned |
| W3 | G. Full Test Suite | ⏳ Planned |

---

## Notes and assumptions

- The spec's formula `expected_sales = goods_sold / (1 + margin)` is implemented
  literally. With a positive margin this makes `expected_sales < goods_sold`;
  the dataset and verdicts are self-consistent with that formula. `goods_sold`
  is the shop's purchases (cost of goods); `expected_sales` is the declared
  sales band implied by the category margin.
- `kirana_overall` is modelled as an aggregate, not a leaf shop category, so the
  "8 shop categories" and the 9 listed margin figures are consistent.
- Test DBs use in-memory SQLite (`StaticPool`, single connection) so API writes
  are visible to direct queries in the same test.
- `data/synthetic/*.csv` is gitignored (generated); `tests/golden_expected.csv`
  is the committed regression lock.
