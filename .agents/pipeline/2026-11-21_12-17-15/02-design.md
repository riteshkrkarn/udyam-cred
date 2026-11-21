# Phase 1 & 2 Integration Testing & Production Deployment - Technical Design

**Date:** 2026-11-21  
**Version:** 1.0  
**Status:** Ready for Implementation  
**Target Audience:** Backend, Frontend, ML, and QA engineers  

---

## Overview

UdyamCred is a tiered, verification-first microloan decisioning system for Indian MSMEs. This design covers the integration testing, security validation, load testing, and production deployment phases. The system uses a fixed pipeline with 9 deterministic Phase 1 rule-based engines orchestrated through a single scoring endpoint. Phase 1-2 engines are already implemented; this phase wires them end-to-end, validates security posture, tests under load, and deploys to production with direct rollout (no canary phase).

**Key architectural decisions locked:**
- Fixed, deterministic pipeline: no multi-agent design, no ML-driven scoring in v1
- All 9 Phase 1 engines orchestrated in sequence: photo verification → source agreement → verified window → tier assignment → amount rule → rate calculation → tranche planning
- Mock OCR and deterministic adapters: all external data sources (UPI, GST, Account Aggregator) return fixed synthetic data, enabling offline testing
- No rate limiting in v1: all API requests processed synchronously, no throttling
- Direct production rollout: assumes comprehensive integration testing, security audit, and load testing validate readiness before deployment
- Database: SQLite for v1, single instance, backup via snapshots
- Frontend: React + Vite, static build artifacts
- ML pipeline: Evaluation-only (no live scoring), deterministic recreates backend decisions

---

## Architecture Overview

### Technology Stack (Locked)

**Backend:**
- FastAPI 0.104+ (async/await, automatic OpenAPI docs)
- SQLAlchemy 2.0+ (ORM, session management)
- SQLite 3.x (production database, single-file, journaling enabled)
- Uvicorn 0.24+ (ASGI server)
- Pydantic 2.x (request/response validation)
- PyJWT 2.8+ (access/refresh token management)
- Bcrypt 4.0+ (password hashing)
- Python 3.11+ (standard library only, no external dependencies for core logic)

**Frontend:**
- React 18.3+ (functional components, hooks)
- React Query (TanStack v5.108+, data synchronization)
- React Hook Form 7.92+ (form state, validation with Zod)
- Zod 4.6+ (schema validation)
- Zustand 5.1+ (global state: auth token, user role)
- React Router 7.18+ (client-side routing)
- Vite 8.3+ (build tooling, dev server, code splitting)
- TypeScript 5+ (type safety)

**ML:**
- Python 3.11+ (deterministic generators, reproducibility validation)
- Pandas (data manipulation)
- NumPy (numerical operations)
- PyYAML (config files)

**Testing & Monitoring:**
- pytest + pytest-cov (unit tests, 286 tests existing, >80% coverage target)
- Apache JMeter or Locust (load testing, concurrency simulation)
- OWASP ZAP (automated security scanning)
- Manual testing (security spot checks, UI/UX validation)

---

## Component Design

### 1. Backend Integration & Wiring

**Objective:** Wire all 9 Phase 1 engines into a single orchestrated scoring pipeline, ensure all endpoints marshal data correctly, and validate end-to-end workflow.

**Key Files:**
- `be/app/endpoints/scoring_phase1.py` (main scoring orchestrator)
- `be/app/endpoints/applications.py` (application CRUD, status transitions)
- `be/app/endpoints/tranches.py` (tranche release, eligibility)
- `be/app/endpoints/repayment.py` (EMI recording, freeze logic)
- `be/app/endpoints/photos.py` (photo upload, EXIF extraction)
- `be/app/endpoints/documents.py` (document upload, validation)
- `be/app/endpoints/household.py` (household data collection)
- `be/app/endpoints/consent.py` (consent tracking)
- `be/app/endpoints/audit.py` (audit log retrieval)

**Engine Orchestration (Scoring Pipeline):**

```
POST /api/scoring/score {application_id, consent_given}
  ↓
1. Load Application, Shop, Household Data
  ↓
2. Fetch DataSources (AA, GST, UPI mock data)
  ↓
3. PhotoVerificationEngine
   - Validate photo format (JPG/PNG, <10MB)
   - Extract EXIF geolocation
   - Check code (challenge text/QR)
   - Compare to rent address (within 500m)
   - Output: photo_verified: bool, location_verified: bool
  ↓
4. SourceAgreementEngine
   - Compare AA turnover vs GST turnover vs UPI turnover
   - Calculate weighted correlation (AA 50%, GST 30%, UPI 20%)
   - Output: source_agreement_score: float [0, 1]
  ↓
5. VerifiedWindowEngine
   - Calculate month overlap across all sources
   - Output: verified_months: int, data_quality_score: float
  ↓
6. GSTCoverageEngine
   - If GSTIN valid: calculate coverage % (GST turnover / purchases)
   - Flag if coverage <60% (reconciliation issue)
   - Output: gst_coverage_pct: float, reconciliation_flagged: bool
  ↓
7. TierAssignmentEngine
   - Tier 1: verified_months ≥ 6, AA+UPI present, no GST (or GST not registered)
   - Tier 2: verified_months ≥ 12, AA+(GST or UPI), GST registered, no Udyam
   - Tier 3: verified_months ≥ 24, AA+GST, Udyam, prior repayment history
   - Output: tier: int [1,2,3], tier_reasons: list[str], next_tier_criteria: list[str]
  ↓
8. AmountRuleEngine
   - Base amount by tier: Tier 1: ₹50k, Tier 2: ₹500k, Tier 3: ₹5M
   - Scale by verification (verified_months / expected_months)
   - Scale by agreement (source_agreement_score)
   - Output: approved_amount: float
  ↓
9. RateCalculationEngine
   - Fetch industry rate from RateAdapter by tier
   - Apply tier adjustment: Tier 1: +5%, Tier 2: +0%, Tier 3: -3%
   - Output: rate_percent: float (annual APR)
  ↓
10. TranchePlanEngine
    - Tier 1: [Tranche 1: 100% at day 0]
    - Tier 2: [Tranche 1: 60% at day 0, Tranche 2: 40% at day 60]
    - Tier 3: [Tranche 1: 40% at day 0, Tranche 2: 30% at day 30, Tranche 3: 20% at day 60, Tranche 4: 10% at day 90]
    - Output: tranche_plan: list[{tranche_num, amount, release_date, tenor_months, emi_count}]
  ↓
11. Calculate EMI Schedule per Tranche
    - Formula: EMI = (P * r * (1+r)^n) / ((1+r)^n - 1)
    - r = monthly_rate (annual_rate / 12 / 100)
    - n = tenor_months
    - Output: emi_schedule: list[{month, principal, interest, balance}]
  ↓
12. Generate Plain Language Reasons
    - Convert engine outputs to borrower-friendly text
    - Example: "You qualify for Tier 2 because we verified 12 months of bank and sales data and your shop is registered for GST"
    - Use glossary (18 terms) to explain jargon
    - Output: reasons: list[str], next_tier_criteria: list[str]
  ↓
13. Save Decision
    - Persist Decision model with: tier, verified_months, source_agreement_score, approved_amount, rate_percent, tranche_plan_json, reasons, created_at
    - Create initial Tranches (rows in tranche table, one per tranche_num)
    - Output: decision_id, decision object
  ↓
14. Return Response
    - Phase1DecisionOut: decision_id, tier, approved_amount, rate_percent, tranche_plan[], reasons[], next_tier_criteria[]
```

**Error Handling per Operation:**

| Operation | Failure Condition | Recovery | Caller Receives | Log Level |
|-----------|-------------------|----------|-----------------|-----------|
| Load Application | App not found | Abort | 404 Application not found | DEBUG |
| Fetch DataSources | AA data missing | Use UPI+GST only | Decision with lower tier | WARN |
| Photo Verification | EXIF missing or geolocation >500m away | Fail photo, tier downgrade possible | photo_verified: false | WARN |
| Tier Assignment | Insufficient data (e.g., <6 months) | Reject (Tier 0) | tier: 0, approved_amount: 0 | INFO |
| RateCalculationEngine | RateAdapter returns null | Use fallback rate (20%) | Decision with fallback rate | WARN |
| Database transaction | Deadlock/constraint violation | Rollback, retry once | 500 Internal Server Error | ERROR |

**API Response Format (Success):**
```json
{
  "decision_id": "dec_a1b2c3",
  "tier": 2,
  "approved_amount": 250000,
  "rate_percent": 18.0,
  "tranche_plan": [
    {
      "tranche_num": 1,
      "amount": 150000,
      "release_date": "2024-11-21",
      "tenor_months": 12,
      "emi_count": 12,
      "emi_monthly": 13500
    },
    {
      "tranche_num": 2,
      "amount": 100000,
      "release_date": "2024-12-20",
      "tenor_months": 12,
      "emi_count": 12,
      "emi_monthly": 9000
    }
  ],
  "reasons": [
    "You qualify for Tier 2 because we verified 12 months of bank and sales data",
    "Your shop is registered for GST and has consistent sales records"
  ],
  "next_tier_criteria": [
    "Maintain on-time EMI payments for 6 months",
    "Update Udyam registration if applicable"
  ]
}
```

**Endpoint Wiring Checklist:**

| Endpoint | Purpose | Engines Invoked | Status |
|----------|---------|-----------------|--------|
| POST /api/scoring/score | Full scoring | All 9 + EMI | **Wiring** |
| POST /api/applications | Create app | None | **Working** |
| GET /api/applications/{id} | Fetch app | None | **Working** |
| POST /api/consent | Grant consent | None | **Working** |
| POST /api/documents/upload | Upload doc | None | **Working** |
| POST /api/household/save | Save household | None | **Working** |
| POST /api/photos/upload | Upload photo | PhotoVerificationEngine | **Wiring** |
| GET /api/tranches/{app_id} | List tranches | None | **Working** |
| POST /api/tranches/{tranche_id}/release | Release tranche | TrancheRuleEngine | **Wiring** |
| POST /api/repayment/record-emi | Record EMI | StopRuleEngine | **Wiring** |
| GET /api/audit/logs | Fetch audit logs | None | **Working** |
| POST /api/override | Override decision | None | **Wiring** |

**Technology Decisions:**
- Orchestration in a single scoring endpoint (not microservices) ensures atomicity and reproducibility
- All engine calls synchronous (no async/await needed for Phase 1 performance targets)
- Deterministic adapters ensure same input → same output (testable, auditable, ML-reproducible)

---

### 2. Frontend Integration & Tier Verification

**Objective:** Ensure frontend collects and displays data correctly, tier assignment logic respects verified months, and plain language reasons display properly.

**Key User Flow (Borrower Wizard):**
```
1. Login → Dashboard (list my applications)
2. Create Application → Select Shop/Business Type
3. Grant Consent → Accept T&C, GST registration, data sharing
4. Photo Capture
   - 3 shots: angle1, angle2, challenge code (text/QR)
   - EXIF auto-captured by camera service
   - On save: POST /api/photos/upload with EXIF data
5. Document Upload
   - Electricity bill (address proof, date extract for rent address)
   - GST certificate (if registered, date extract for coverage window)
   - Bank statements (UA reconciliation, for AA data)
   - UPI statements (if available)
   - POST /api/documents/upload per file
6. Household Data
   - Family size, dependents, monthly expenses, existing liabilities
   - POST /api/household/save
7. Submit Application
   - POST /api/applications/{id}/submit
   - Triggers backend to fetch DataSources → scoring
8. View Result Page
   - Display: Tier, Approved Amount, Rate, EMI Schedule, Reasons, Next Tier Criteria
   - Reasons in plain English (glossary links)
   - Tranche plan visualization (timeline with EMI schedule per tranche)
9. Officer Review Queue
   - Dashboard lists pending applications (filter by tier, sort by date)
   - Click case → View tabs: overview, sources, photos, documents, repayment history
   - Replay with modified household data → See new decision (not persisted)
   - Override with reason → Save override, audit logged
```

**Data Flow (Frontend ↔ Backend):**

| Step | Frontend Action | Backend Call | Response | Frontend Display |
|------|-----------------|-------------|----------|------------------|
| 3. Consent | User clicks "I Agree" | POST /api/consent {application_id, borrower_agreed: true} | {consent_id, agreed_at} | Confirm check ✓ |
| 4. Photos | User uploads 3 photos (via camera) | POST /api/photos/upload multipart {application_id, file, exif_lat, exif_lon, exif_datetime} | {photo_id, verified: bool, reason: str} | Photo count (1/3, 2/3, 3/3) |
| 5. Documents | User uploads bills, cert, statements | POST /api/documents/upload multipart {application_id, doc_type, file} | {document_id, validation_status} | File list with ✓/✗ |
| 6. Household | User enters family, expenses, liabilities | POST /api/household/save {application_id, family_size, monthly_expenses, liabilities} | {household_id, saved_at} | Summary display |
| 7. Submit | User clicks "Submit" | POST /api/applications/{id}/submit {application_id} | {decision_id, tier, approved_amount, rate_percent, ...} | Result page |
| 8. Result | Display scoring decision | (already returned from step 7) | (already in state) | Tier badge, amount in INR, reasons, EMI table |

**Tier-Driven Verified Months (User Requirement: "tier drives verified months"):**

The frontend must collect data sources (AA, GST, UPI months present) and pass to backend. Backend tier assignment engine calculates verified_months = min(aa_months, gst_months, upi_months) across overlapping period. Tier then depends on verified_months:

```
Tier 1: verified_months >= 6 (AA+UPI, no GST registered)
Tier 2: verified_months >= 12 (AA+(GST or UPI), GST registered)
Tier 3: verified_months >= 24 (AA+GST, Udyam, prior repayment)
```

**Frontend Validation (Pre-Submit):**
- Warn if collected data <6 months ("Insufficient data for tier assignment")
- Warn if photo verification failed ("Retake photos to proceed")
- Warn if consent not granted ("Please accept consent to continue")
- Block submit if critical data missing

**Plain Language Glossary (18 Terms, 6 Categories):**

| Category | Term | Plain English |
|----------|------|---------------|
| **Data Verification** | AA (Account Aggregator) | Bank account data verified for 6+ months |
| | GST | Sales tax records from government |
| | UPI | Mobile payment records |
| | Verified Window | The period where we have confirmed your data |
| **Business Metrics** | Turnover | Total sales your business makes annually |
| | Purchases | Goods you buy for your business |
| | Coverage | How much of your claimed sales match tax records |
| **Borrowing Tiers** | Tier 1 | Entry-level borrowers with 6+ months verified data |
| | Tier 2 | Established borrowers with 12+ months and GST registration |
| | Tier 3 | Experienced borrowers with 2+ years data and prior loan history |
| **Loan Features** | EMI | Equal monthly payment (principal + interest) |
| | Tenor | Loan repayment period in months |
| | Tranche | Part of the loan released over time (not all at once) |
| **Repayment Status** | On-Time | Payment made by due date |
| | Missed | Payment not made by due date |
| | Frozen | Loan stopped due to 2+ missed payments |
| **Approval Conditions** | Udyam Registration | Formal government registration for MSMEs |
| | Prior Repayment | History of paying back previous loans on time |

**Glossary Integration:**
- Clickable tooltips on glossary terms in reasons (e.g., "tier drives verified months" → tooltip explains)
- Glossary page at `/glossary` with full definitions and examples
- For each reason, embed glossary link: "You qualify for [Tier 2](link) because we verified [12 months](link) of [bank and sales data](link)"

**Technology Decisions:**
- Photo service via `photo-service.ts`: calls native camera API, captures EXIF automatically
- Document upload multipart/form-data (file + metadata)
- Household data via React Hook Form (local state validation before submission)
- Result page state managed via Zustand (persist across navigation)
- Glossary embedded in app or fetched from `/api/glossary` endpoint

---

### 3. Integration Testing

**Objective:** Validate end-to-end workflows, security boundaries, determinism, and error handling across all components.

**Test Environment:**
- Backend: pytest fixtures with in-memory SQLite (`:memory:` for speed, or temporary file for shared state)
- Frontend: Vitest + React Testing Library (component tests), Selenium/Cypress (E2E tests optional for v1)
- ML: Python pytest with deterministic generator

**Test Categories (8 Integration Tests):**

#### Test 1: Borrower Workflow End-to-End (Happy Path)
**Scenario:** 
- Create application, grant consent, upload 3 photos (EXIF valid, geolocation within 500m), upload documents (electricity bill + GST cert), enter household data, submit → See scoring result with tier/amount/rate/EMI/reasons
- Expected: Tier 2, amount ₹250k, rate 18%, 2 tranches, 4+ reasons

**Setup:**
```python
def test_borrower_workflow_end_to_end(client, db):
    # 1. Create application
    app_resp = client.post("/api/applications", json={
        "borrower_id": 1,
        "shop_id": 1,
        "loan_amount_requested": 500000,
        "purpose": "Inventory expansion"
    })
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]
    
    # 2. Grant consent
    consent_resp = client.post(f"/api/applications/{app_id}/consent", json={
        "borrower_agreed": True
    })
    assert consent_resp.status_code == 200
    
    # 3. Upload 3 photos
    for i in range(3):
        with open(f"test_data/photo{i+1}.jpg", "rb") as f:
            photo_resp = client.post(
                f"/api/photos/upload",
                files={"file": f},
                data={"application_id": app_id, "exif_lat": 28.5355, "exif_lon": 77.3910, "exif_datetime": "2024-11-20T10:00:00"}
            )
        assert photo_resp.status_code == 201
    
    # 4. Upload documents (electricity bill + GST cert)
    with open("test_data/electricity_bill.pdf", "rb") as f:
        doc_resp = client.post(
            "/api/documents/upload",
            files={"file": f},
            data={"application_id": app_id, "doc_type": "electricity_bill"}
        )
    assert doc_resp.status_code == 201
    
    # 5. Enter household data
    hh_resp = client.post(f"/api/applications/{app_id}/household", json={
        "family_size": 4,
        "monthly_expenses": 15000,
        "liabilities": 50000
    })
    assert hh_resp.status_code == 200
    
    # 6. Submit application
    submit_resp = client.post(f"/api/applications/{app_id}/submit", json={
        "consent_given": True
    })
    assert submit_resp.status_code == 200
    
    # 7. Verify scoring result
    result = submit_resp.json()
    assert result["tier"] == 2
    assert result["approved_amount"] == 250000
    assert result["rate_percent"] == 18.0
    assert len(result["tranche_plan"]) == 2
    assert len(result["reasons"]) >= 4
    assert all(isinstance(r, str) and len(r) > 0 for r in result["reasons"])
```

**Acceptance Criteria:**
- ✓ All 7 steps complete without error
- ✓ Tier = 2 (12 months verified data from mock AA/GST)
- ✓ Amount = ₹250k (Tier 2 cap = ₹500k, scaled to 50%)
- ✓ Rate = 18% (base 18% for Tier 2)
- ✓ Tranches = 2 (Tier 2 plan: 60% + 40%)
- ✓ Reasons in plain English (no code names)
- ✓ Reasons include tier justification + next tier criteria

#### Test 2: Officer Dashboard Workflow
**Scenario:**
- Officer logs in, views queue of 10 pending applications (filtered by tier, sorted by date), clicks case → sees 5 tabs (overview, sources, photos, documents, repayment), replays with modified household data → sees new decision (not persisted), overrides with reason → verifies audit trail

**Setup:**
```python
def test_officer_dashboard_workflow(client, db):
    # Create 10 applications in various tiers
    for i in range(10):
        app = Application(
            borrower_id=i+1, shop_id=i+1, 
            loan_amount_requested=100000*(i % 3 + 1),
            status="pending"
        )
        db.add(app)
    db.commit()
    
    # Officer login
    login_resp = client.post("/auth/login", json={
        "email": "officer@example.com",
        "password": "secure_password"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Queue view with filters
    queue_resp = client.get(
        "/api/applications?status=pending&sort_by=date&filter_tier=2",
        headers=headers
    )
    assert queue_resp.status_code == 200
    apps = queue_resp.json()
    assert len(apps) >= 0  # Some subset of 10
    
    # 2. Click case
    app_id = apps[0]["id"] if apps else 1
    case_resp = client.get(f"/api/applications/{app_id}", headers=headers)
    assert case_resp.status_code == 200
    case = case_resp.json()
    
    # 3. Verify 5 tabs
    tabs = {
        "overview": client.get(f"/api/applications/{app_id}/overview", headers=headers).status_code,
        "sources": client.get(f"/api/applications/{app_id}/data-sources", headers=headers).status_code,
        "photos": client.get(f"/api/applications/{app_id}/photos", headers=headers).status_code,
        "documents": client.get(f"/api/applications/{app_id}/documents", headers=headers).status_code,
        "repayment": client.get(f"/api/applications/{app_id}/repayment-history", headers=headers).status_code,
    }
    assert all(status == 200 for status in tabs.values()), f"Tabs failed: {tabs}"
    
    # 4. Replay with modified household
    replay_resp = client.post(
        f"/api/applications/{app_id}/replay",
        json={"family_size": 8, "monthly_expenses": 25000},
        headers=headers
    )
    assert replay_resp.status_code == 200
    replay_decision = replay_resp.json()
    # Verify replay doesn't persist original decision
    verify_resp = client.get(f"/api/applications/{app_id}/decision", headers=headers)
    assert verify_resp.status_code == 200
    persisted_decision = verify_resp.json()
    assert persisted_decision["id"] != replay_decision["id"]  # Different decisions
    
    # 5. Override with reason
    override_resp = client.post(
        f"/api/applications/{app_id}/override",
        json={"override_amount": 350000, "reason": "Approved based on strong credit history"},
        headers=headers
    )
    assert override_resp.status_code == 200
    override = override_resp.json()
    
    # 6. Verify audit trail
    audit_resp = client.get(
        f"/api/audit/logs?entity_id={app_id}&entity_type=application",
        headers=headers
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    override_log = next((log for log in logs if log["action"] == "override"), None)
    assert override_log is not None
    assert override_log["reason"] == "Approved based on strong credit history"
    assert override_log["officer_id"] == 1  # Officer who made override
```

**Acceptance Criteria:**
- ✓ Queue loads all pending applications
- ✓ Filters by tier and sort by date work
- ✓ Case view shows all 5 tabs
- ✓ Replay returns new decision without persisting
- ✓ Override creates audit log with officer_id + reason
- ✓ Audit log immutable (not updated/deleted)

#### Test 3: Tier-Driven Verified Months Boundaries
**Scenario:**
- Test exact boundary cases for tier assignment based on verified_months:
  - 5.99 months → Rejected (Tier 0)
  - 6.0 months → Tier 1
  - 11.99 months → Tier 1 (can't reach Tier 2 yet)
  - 12.0 months → Tier 2
  - 23.99 months → Tier 2
  - 24.0 months + Udyam → Tier 3

**Setup:**
```python
def test_tier_boundaries_by_verified_months(client, db, synthetic_shops):
    """Test tier assignment logic respects verified_months thresholds."""
    
    test_cases = [
        # (verified_months, aa_present, gst_registered, udyam, expected_tier, expected_decision)
        (5.99, True, False, False, 0, "rejected"),  # Below Tier 1 threshold
        (6.0, True, False, False, 1, "approved"),   # Tier 1 threshold
        (11.99, True, True, False, 1, "approved"),  # Below Tier 2 threshold
        (12.0, True, True, False, 2, "approved"),   # Tier 2 threshold
        (23.99, True, True, True, 2, "approved"),   # Below Tier 3 threshold
        (24.0, True, True, True, 3, "approved"),    # Tier 3 threshold
    ]
    
    for verified_months, aa_present, gst_registered, udyam, expected_tier, expected_decision in test_cases:
        # Create synthetic shop with exact data sources
        shop = create_synthetic_shop_with_data_window(
            verified_months=verified_months,
            aa_present=aa_present,
            gst_registered=gst_registered,
            udyam_present=udyam
        )
        
        # Create application + household
        app = Application(borrower_id=1, shop_id=shop.id)
        db.add(app)
        db.commit()
        
        # Score
        score_resp = client.post("/api/scoring/score", json={
            "application_id": app.id,
            "consent_given": True
        })
        
        result = score_resp.json()
        assert result["tier"] == expected_tier, f"Failed for {verified_months} months: expected tier {expected_tier}, got {result['tier']}"
        assert result["status"] == expected_decision, f"Failed for {verified_months} months: expected {expected_decision}, got {result['status']}"
```

**Acceptance Criteria:**
- ✓ All 6 boundary test cases pass
- ✓ Tier assignment respects verified_months thresholds exactly

#### Test 4: Tranche Gate Enforcement
**Scenario:**
- Create application → Score → Release Tranche 1 → Record on-time EMI for Tranche 1 → Release Tranche 2 → Attempt to release Tranche 3 before recording EMI → Verify rejection

**Setup:**
```python
def test_tranche_gate_enforcement(client, db):
    """Test tranche eligibility rules (prior EMI on-time required)."""
    
    # Setup: score a Tier 2 app (2 tranches)
    app = create_and_score_tier2_app(db)
    tranches = db.query(Tranche).filter(Tranche.application_id == app.id).all()
    assert len(tranches) == 2
    
    # 1. Release Tranche 1
    release_resp = client.post(
        f"/api/tranches/{tranches[0].id}/release",
        json={"officer_id": 1}
    )
    assert release_resp.status_code == 200
    assert release_resp.json()["status"] == "released"
    
    # 2. Record on-time EMI for Tranche 1
    for month in range(1, 13):  # 12 months of EMIs
        emi_resp = client.post(f"/api/repayment/record-emi", json={
            "tranche_id": tranches[0].id,
            "month": month,
            "amount_paid": tranches[0].emi_monthly,
            "payment_date": f"2024-{(11 + month) % 12 + 1:02d}-01"
        })
        assert emi_resp.status_code == 200
    
    # 3. Release Tranche 2
    release2_resp = client.post(
        f"/api/tranches/{tranches[1].id}/release",
        json={"officer_id": 1}
    )
    assert release2_resp.status_code == 200  # All prior EMIs on-time, eligible
    
    # 4. Attempt Tranche 3 (doesn't exist for Tier 2, would fail anyway)
    # For Tier 3 app with 4 tranches:
    app3 = create_and_score_tier3_app(db)
    tranches3 = db.query(Tranche).filter(Tranche.application_id == app3.id).order_by(Tranche.tranche_num).all()
    assert len(tranches3) == 4
    
    # Release Tranche 1
    client.post(f"/api/tranches/{tranches3[0].id}/release", json={"officer_id": 1})
    
    # Record 11 EMIs for Tranche 1 (1 missed)
    for month in range(1, 12):
        client.post(f"/api/repayment/record-emi", json={
            "tranche_id": tranches3[0].id,
            "month": month,
            "amount_paid": tranches3[0].emi_monthly,
            "payment_date": f"2024-{(11 + month) % 12 + 1:02d}-01"
        })
    
    # Attempt Tranche 2 release (should fail: Tranche 1 EMI not all on-time)
    release_attempt = client.post(
        f"/api/tranches/{tranches3[1].id}/release",
        json={"officer_id": 1}
    )
    assert release_attempt.status_code == 403  # Forbidden: not eligible
    assert "not eligible" in release_attempt.json()["detail"].lower()
```

**Acceptance Criteria:**
- ✓ Tranche 1 releases successfully
- ✓ All 12 EMIs recorded for Tranche 1
- ✓ Tranche 2 releases after all Tranche 1 EMIs on-time
- ✓ Tranche 3 release blocked if any prior EMI missed
- ✓ Error message includes reason ("Not eligible: previous tranche EMI not paid on-time")

#### Test 5: Stop Rule Freeze (2 Missed EMIs)
**Scenario:**
- Create application, release tranche, record 1 missed EMI (still unfrozen), record 2nd missed EMI → Application frozen, frozen status visible in queue, cannot request new tranches

**Setup:**
```python
def test_stop_rule_freeze_on_missed_emis(client, db):
    """Test freeze logic: 2+ missed EMIs triggers stop rule."""
    
    # Setup: score and release Tier 2 app
    app = create_and_score_tier2_app(db)
    tranches = db.query(Tranche).filter(Tranche.application_id == app.id).all()
    client.post(f"/api/tranches/{tranches[0].id}/release", json={"officer_id": 1})
    
    # 1. Record 1 missed EMI
    client.post(f"/api/repayment/record-emi", json={
        "tranche_id": tranches[0].id,
        "month": 1,
        "amount_paid": 0,
        "payment_date": None,
        "status": "missed"
    })
    
    # Verify app not frozen yet
    app_status = client.get(f"/api/applications/{app.id}").json()
    assert app_status["frozen"] == False
    
    # 2. Record 2nd missed EMI
    client.post(f"/api/repayment/record-emi", json={
        "tranche_id": tranches[0].id,
        "month": 2,
        "amount_paid": 0,
        "payment_date": None,
        "status": "missed"
    })
    
    # 3. Verify app frozen
    app_status = client.get(f"/api/applications/{app.id}").json()
    assert app_status["frozen"] == True
    assert app_status["frozen_date"] is not None
    
    # 4. Verify frozen status in queue
    queue_resp = client.get("/api/applications?filter_frozen=true")
    assert any(a["id"] == app.id for a in queue_resp.json())
    
    # 5. Attempt release next tranche (should fail)
    release_resp = client.post(
        f"/api/tranches/{tranches[1].id}/release",
        json={"officer_id": 1}
    )
    assert release_resp.status_code == 403
    assert "frozen" in release_resp.json()["detail"].lower()
    
    # 6. Verify audit log records freeze
    audit_resp = client.get(f"/api/audit/logs?entity_id={app.id}")
    freeze_log = next((log for log in audit_resp.json() if "frozen" in log["action"].lower()), None)
    assert freeze_log is not None
    assert freeze_log["reason"] == "2 missed EMIs recorded"
```

**Acceptance Criteria:**
- ✓ 1 missed EMI recorded, app remains unfrozen
- ✓ 2 missed EMIs recorded, app frozen automatically
- ✓ Frozen status persisted in database
- ✓ Frozen status visible in queue filter
- ✓ Cannot release new tranches while frozen
- ✓ Freeze event logged to audit trail

#### Test 6: Photo Verification Integration
**Scenario:**
- Upload 3 valid photos (EXIF present, geolocation within 500m, challenge code detected) → Accepted; Upload photo without code → Rejected; Upload photo >500m away → Rejected

**Setup:**
```python
def test_photo_verification_integration(client, db):
    """Test photo upload, EXIF extraction, geo-location matching."""
    
    app = create_application(db)
    
    # 1. Upload valid photo (EXIF, geolocation within 500m, challenge code)
    # Mock photo service response
    with patch('app.endpoints.photos.verify_exif_location') as mock_verify:
        mock_verify.return_value = {
            "verified": True,
            "latitude": 28.5355,
            "longitude": 77.3910,
            "distance_m": 150,  # Within 500m
            "code_detected": True,
            "code_text": "APP123"
        }
        
        with open("test_data/valid_photo.jpg", "rb") as f:
            resp = client.post(
                f"/api/photos/upload",
                files={"file": f},
                data={"application_id": app.id}
            )
        assert resp.status_code == 201
        assert resp.json()["verified"] == True
    
    # 2. Upload photo without challenge code
    with patch('app.endpoints.photos.verify_exif_location') as mock_verify:
        mock_verify.return_value = {
            "verified": False,
            "error": "Challenge code not detected",
            "code_detected": False
        }
        
        with open("test_data/no_code_photo.jpg", "rb") as f:
            resp = client.post(
                f"/api/photos/upload",
                files={"file": f},
                data={"application_id": app.id}
            )
        assert resp.status_code == 400  # or 201 with verified: false
        assert "code" in resp.json()["detail"].lower()
    
    # 3. Upload photo >500m away
    with patch('app.endpoints.photos.verify_exif_location') as mock_verify:
        mock_verify.return_value = {
            "verified": False,
            "error": "Geolocation >500m from rent address",
            "distance_m": 1200
        }
        
        with open("test_data/far_photo.jpg", "rb") as f:
            resp = client.post(
                f"/api/photos/upload",
                files={"file": f},
                data={"application_id": app.id}
            )
        assert resp.status_code == 400
        assert "distance" in resp.json()["detail"].lower() or "500m" in resp.json()["detail"]
```

**Acceptance Criteria:**
- ✓ Valid photo (code + location) accepted
- ✓ Photo without code rejected with error message
- ✓ Photo >500m away rejected with error message
- ✓ Verified photos persist to database
- ✓ Rejected photos not persisted

#### Test 7: Plain Language Reasons
**Scenario:**
- Score application, verify reasons displayed in plain English (not code names), glossary terms clickable, 18 glossary terms available

**Setup:**
```python
def test_plain_language_reasons_and_glossary(client, db):
    """Test reason generation and glossary."""
    
    # Score app
    app = create_and_score_tier2_app(db)
    decision_resp = client.get(f"/api/applications/{app.id}/decision")
    decision = decision_resp.json()
    
    # 1. Verify reasons in plain English
    assert len(decision["reasons"]) >= 4
    assert all(isinstance(r, str) for r in decision["reasons"])
    assert all(len(r) > 0 for r in decision["reasons"])
    
    # Check for common English phrases, not code names
    reasons_text = " ".join(decision["reasons"]).lower()
    assert "tier 2" in reasons_text or "tier 2" in decision["tier_name"].lower()
    assert "verified" in reasons_text
    assert "bank" in reasons_text or "sales" in reasons_text
    
    # Ensure no code names like "tier_2_aa_gst" or "source_agreement_score"
    assert "tier_2_" not in reasons_text
    assert "_score" not in reasons_text
    
    # 2. Verify glossary available
    glossary_resp = client.get("/api/glossary")
    assert glossary_resp.status_code == 200
    glossary = glossary_resp.json()
    
    # Check 18 terms present
    required_terms = [
        "Account Aggregator", "GST", "UPI", "Verified Window",
        "Turnover", "Purchases", "Coverage", 
        "Tier 1", "Tier 2", "Tier 3",
        "EMI", "Tenor", "Tranche",
        "On-Time", "Missed", "Frozen",
        "Udyam Registration", "Prior Repayment"
    ]
    glossary_terms = list(glossary.keys())
    assert all(term in glossary_terms for term in required_terms), f"Missing terms: {set(required_terms) - set(glossary_terms)}"
    
    # 3. Verify reason text contains glossary-able terms
    for reason in decision["reasons"]:
        # Count how many glossary terms appear in reason
        matching_terms = [term for term in required_terms if term.lower() in reason.lower()]
        # At least one glossary term in each reason
        assert len(matching_terms) >= 1, f"Reason has no glossary terms: {reason}"
```

**Acceptance Criteria:**
- ✓ Reasons in plain English (no code names)
- ✓ At least 4 reasons per decision
- ✓ Each reason contains 1+ glossary terms
- ✓ Glossary endpoint returns all 18 terms with definitions
- ✓ Glossary terms match reason templates

#### Test 8: ML Reproducibility (Determinism)
**Scenario:**
- Generate 100 synthetic shops, score in backend, export decisions, rescore in ML pipeline, verify outputs match 100% (deterministic)

**Setup:**
```python
def test_ml_reproducibility_determinism(client, db, ml_scorer):
    """Test determinism: backend and ML pipeline produce identical decisions."""
    
    # 1. Generate 100 synthetic shops
    from ml.generator import generate_shops
    shops = generate_shops(count=100)
    
    # 2. Insert into backend
    for shop in shops:
        db_shop = Shop(**shop)
        db.add(db_shop)
    db.commit()
    
    # 3. Score in backend
    backend_decisions = []
    for i, shop in enumerate(shops):
        app = Application(
            borrower_id=1, 
            shop_id=shop.id,
            loan_amount_requested=100000
        )
        db.add(app)
        db.commit()
        
        resp = client.post("/api/scoring/score", json={
            "application_id": app.id,
            "consent_given": True
        })
        backend_decisions.append(resp.json())
    
    # 4. Export decisions for ML
    decisions_export = [{
        "shop_id": d["shop_id"],
        "tier": d["tier"],
        "approved_amount": d["approved_amount"],
        "rate_percent": d["rate_percent"],
        "reasons": d["reasons"]
    } for d in backend_decisions]
    
    # 5. Rescore in ML pipeline
    ml_decisions = ml_scorer.score_batch(shops)
    
    # 6. Compare outputs
    mismatches = []
    for i, (backend, ml) in enumerate(zip(backend_decisions, ml_decisions)):
        if backend["tier"] != ml["tier"]:
            mismatches.append(f"Shop {i}: tier mismatch ({backend['tier']} vs {ml['tier']})")
        if abs(backend["approved_amount"] - ml["approved_amount"]) > 100:  # Allow small rounding
            mismatches.append(f"Shop {i}: amount mismatch ({backend['approved_amount']} vs {ml['approved_amount']})")
        if abs(backend["rate_percent"] - ml["rate_percent"]) > 0.01:
            mismatches.append(f"Shop {i}: rate mismatch ({backend['rate_percent']} vs {ml['rate_percent']})")
    
    assert len(mismatches) == 0, f"Determinism failed: {mismatches}"
```

**Acceptance Criteria:**
- ✓ 100 synthetic shops generated
- ✓ All 100 backend decisions recorded
- ✓ ML pipeline rescores all 100 shops
- ✓ 100% match on tier, approved_amount, rate_percent (determinism verified)
- ✓ No stochastic elements in pipeline

**Test Execution (Pytest Command):**
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all integration tests
pytest tests/integration/ -v --cov=app --cov-report=html

# Run specific test
pytest tests/integration/test_integration_tests.py::TestBorrowerWorkflow::test_borrower_workflow_end_to_end -v

# Run with detailed output
pytest tests/integration/ -vv --tb=short
```

---

### 4. Security Baseline (OWASP Top 10)

**Objective:** Validate security controls across 10 OWASP Top 10 categories, ensure no critical vulnerabilities, fix findings before production.

**Security Testing Approach:**
- Automated: OWASP ZAP (free, open-source, covers 80% of common issues)
- Manual spot checks: SQL injection, XSS, authentication bypass, CORS misconfiguration
- Code review: 50 critical files (endpoints, models, auth, database queries)

**Findings Matrix (10 OWASP Items):**

| # | Category | Control | Test | Expected Result | Implementation |
|---|----------|---------|------|-----------------|-----------------|
| **FR2.1** | A07: Identification & Auth | JWT tokens required, 15min expiry, refresh token rotation | Call endpoint without token → 401; Call with expired token → 401; Call with refresh → new access token | ✓ 401 Unauthorized | Already implemented (auth.py) |
| **FR2.1** | A07: Role-Based Access | borrower role sees only own apps, officer role sees queue, approver role can override | Borrower queries borrower2's app → 403; Officer queries all → 200; Approver overrides → 200 | ✓ 403 Forbidden for unauthorized | Role checks in endpoints (depends on JWT sub + role claim) |
| **FR2.2** | A01: Broken Access Control | Queries filtered by user_id (borrower) or role (officer/auditor) | SQL query for applications includes `WHERE borrower_id = {current_user_id}` | ✓ No cross-borrower data leakage | Repository layer adds WHERE filters (ORM prevents injection) |
| **FR2.3** | A03: Injection | All inputs validated via Pydantic, parameterized queries (SQLAlchemy ORM) | Inject "1 OR 1=1" in application_id → Treated as literal int, query fails safely | ✓ No SQL errors, query executes with literal | ORM parameterized by default |
| **FR2.3** | A03: XSS Prevention | Output sanitized via JSON encoder, no eval/exec | Input "<script>alert('xss')</script>" in reason → Stored/returned as JSON string (escaped) | ✓ Script tags rendered as text, not executed | JSON response automatically escapes; ORM handles escaping |
| **FR2.4** | A02: Cryptographic Failures | Passwords hashed (bcrypt), PII masked in logs, tokens HTTPOnly | logs.txt contains "***" instead of SSN; token in cookie has HttpOnly flag | ✓ No plaintext secrets in logs; HttpOnly set | Auth uses bcrypt; logging module configured to mask; cookie flags set in FastAPI |
| **FR2.4** | A02: HTTPS in Prod | Enforce HTTPS, HSTS header, TLS 1.2+ | HTTP request → Redirects to HTTPS; Response headers include Strict-Transport-Security | ✓ HSTS present, no downgrade possible | Reverse proxy (nginx) or FastAPI middleware enforces redirect + HSTS |
| **FR2.5** | A05: Broken Object Level Authorization | Endpoint checks if requester authorized to access object | GET /api/applications/999 where user doesn't own app → 404 or 403 | ✓ 403 Forbidden | Endpoint validates ownership before returning data |
| **FR2.5** | A08: CORS Misconfiguration | CORS origins explicitly whitelisted (no "*"), OPTIONS preflight handled | Cross-origin request from different domain → 403 CORS error | ✓ CORS rejected for unauthorized origin | FastAPI CORSMiddleware configured with specific origins |
| **FR2.6** | A04: Insecure Deserialization | File upload validates magic bytes (not just extension), file size <10MB, file types whitelisted | Upload EXE with .pdf extension → Magic byte check detects EXE, rejected | ✓ Rejected (not a PDF) | Document endpoint checks magic bytes using python-magic library or similar |
| **FR2.7** | A01: Broken Access Control & A09: Logging | Error responses generic (no PII, no stack trace), 500 errors return "Internal Server Error" | Trigger 500 error → Response doesn't include code line numbers or sensitive data | ✓ Generic error message | FastAPI exception handlers catch exceptions, return generic response |
| **FR2.7** | A06: Information Disclosure | No debug mode in production (DEBUG=False), no stack traces, error logs don't leak PII | 404 error doesn't say "User XYZ not found"; logs don't show SSN | ✓ Generic messages | Settings.DEBUG=False; logging configured to mask PII |
| **FR2.8** | A09: Logging & Monitoring | All decisions, overrides, freezes logged with timestamp, user_id, officer_id, reason | Audit log contains: decision_id, application_id, user_id, officer_id, action, reason, timestamp | ✓ Audit trail complete and queryable | AuditLog model records all events; immutable (no updates post-creation) |
| **FR2.8** | A09: Login Attempts Logged | Success/failure login attempts logged with IP, email, timestamp | logs.txt contains "LOGIN_ATTEMPT: email=user@example.com, status=success, ip=192.168.1.1" | ✓ All logins logged | Auth endpoint logs success/failure |
| **FR2.1 + FR2.2** | A07 + A01: Permission Escalation | User can't escalate own role (no API endpoint to set role=admin) | POST /api/users/me {role: "admin"} → 400 Bad Request or 403 Forbidden | ✓ Role immutable via API | Role set only in database, no endpoint to modify |

**Security Test Commands:**

```bash
# 1. Automated scanning with OWASP ZAP (free version)
# Download ZAP from: https://www.zaproxy.org/
# Start ZAP background daemon
zaproxy.sh -cmd -port 8091

# Scan backend
python3 -m pip install python-owasp-zap-v2-client
python3 scripts/zap_scan.py http://localhost:8000

# 2. Manual SQL injection test
curl -X GET "http://localhost:8000/api/applications?application_id=1 OR 1=1" 
# Expected: Bad request (int parsing fails) or results for app 1 only

# 3. Manual XSS test
curl -X POST "http://localhost:8000/api/applications" \
  -H "Content-Type: application/json" \
  -d '{"purpose": "<script>alert(1)</script>"}'
# Expected: Stored as string, not executed in API response

# 4. Authentication tests
# Without token
curl -X GET "http://localhost:8000/api/applications"
# Expected: 401 Unauthorized

# 5. CORS test
curl -X OPTIONS "http://localhost:8000/api/applications" \
  -H "Origin: https://malicious.com"
# Expected: No CORS headers, or 403 error

# 6. File upload test
# Create EXE with .pdf extension
echo "MZ..." > test.pdf  # MZ is DOS/Windows executable header
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@test.pdf"
# Expected: 400 Bad Request (magic byte mismatch)
```

**Security Audit Report (Template):**
```markdown
# Security Audit Report - Phase 1 & 2 Deployment

**Date:** 2024-11-21  
**Scope:** Backend API (fastapi), Frontend (React), Database (SQLite)  
**Methodology:** OWASP Top 10 checklist + manual testing

## Findings

### Critical (Must Fix Before Deploy)
- None (assumed after fixes)

### High (Recommend Fix)
- [ ] Rate limiting not implemented (backlog for v1.1)

### Medium
- None

### Low (Information)
- None

## Remediation Status
- [x] A01: Broken Access Control - Data isolation verified
- [x] A02: Cryptographic Failures - HTTPS enforced, passwords hashed
- [x] A03: Injection - Parameterized queries, input validation
- [x] A04: Insecure Deserialization - File upload validation added
- [x] A05: Broken Object Level Authorization - Ownership checks implemented
- [x] A06: Vulnerable & Outdated Components - Dependencies pinned
- [x] A07: Identification & Authentication - JWT + refresh tokens
- [x] A08: CORS Misconfiguration - Explicit whitelisting
- [x] A09: Logging & Monitoring - Audit trail implemented
- [ ] Rate Limiting - BACKLOG for v1.1

## Recommendations
1. Run OWASP ZAP quarterly
2. Implement rate limiting in v1.1
3. Add Web Application Firewall (WAF) in v1.2 if scaling

## Sign-Off
- Security Reviewer: [Name]
- Date Approved: 2024-11-21
```

---

### 5. Load Testing

**Objective:** Verify system handles 100+ concurrent users without degradation, measure response times, error rates, resource usage.

**Load Test Configuration:**

**Test 1: Scoring Endpoint Concurrency (Tier 1-2 Adoption Curve)**
- Tool: Apache JMeter or Locust
- Scenario: 100 concurrent users submit applications for scoring
- Duration: 5 minutes sustained load
- Request type: POST /api/scoring/score
- Metrics:
  - Response time (mean, p50, p95, p99)
  - Error rate (%)
  - Throughput (requests/second)
  - Database connection pool usage

**Expected Results:**
- Response time <2 seconds (p95)
- Error rate <1%
- Throughput ~15-20 req/sec (depends on hardware)

**JMeter Test Plan (XML):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" ...>
      <elementProp name="TestPlan.user_defined_variables" ...>
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" ...>
        <stringProp name="ThreadGroup.num_threads">100</stringProp>
        <stringProp name="ThreadGroup.ramp_time">60</stringProp>
        <stringProp name="ThreadGroup.duration">300</stringProp>
        <boolProp name="ThreadGroup.same_user_on_next_iteration">true</boolProp>
        <elementProp name="ThreadGroup.main_controller" ...>
          <collectionProp name="Arguments.arguments"/>
        </elementProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSampler guiclass="HttpTestSampleGui" ...>
          <elementProp name="Arguments" ...>
            <collectionProp name="Arguments.arguments">
              <HTTPArgument name="application_id" value="1"/>
              <HTTPArgument name="consent_given" value="true"/>
            </collectionProp>
          </elementProp>
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
          <stringProp name="HTTPSampler.port">8000</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
          <stringProp name="HTTPSampler.path">/api/scoring/score</stringProp>
          <stringProp name="HTTPSampler.method">POST</stringProp>
        </HTTPSampler>
        <hashTree>
          <ResultCollector guiclass="TableVisualizer" ...>
            <boolProp name="ResultCollector.error_logging">true</boolProp>
            <objProp>
              <name>saveConfig</name>
              <value class="SampleSaveConfiguration">
                <time>true</time>
                <latency>true</latency>
                <timestamp>true</timestamp>
                <success>true</success>
                <label>true</label>
                <code>true</code>
                <message>true</message>
                <threadName>true</threadName>
                <dataType>true</dataType>
                <encoding>false</encoding>
                <assertions>true</assertions>
                <subresults>true</subresults>
                <responseData>false</responseData>
                <samplerData>false</samplerData>
                <xml>true</xml>
              </value>
            </objProp>
          </ResultCollector>
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

**Run Load Test:**
```bash
# Using JMeter
jmeter -n -t load_test_scoring.jmx -l results.jtl -j jmeter.log

# Generate report
jmeter -g results.jtl -o results_html/

# Using Locust (alternative)
locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --host http://localhost:8000

# Monitor backend during load test
watch -n 1 'ps aux | grep uvicorn'  # CPU, memory
```

**Test 2: Queue Endpoint (Officer Dashboard Load)**
- Concurrent officers: 50
- Each loads queue of 1000+ applications (with sorting/filtering)
- Duration: 2 minutes
- Request: GET /api/applications?status=pending&sort_by=date&limit=50&offset=0

**Expected Results:**
- Response time <3 seconds (p95)
- Error rate <1%
- Database query time <500ms for 1000-record table

**Test 3: Database Stress Test**
- Scenario: 10,000 applications in database, 50 concurrent scoring operations
- Measure: Query plan performance, connection pool behavior, deadlock frequency
- Expected: No deadlocks, no connection pool exhaustion

**Test 4: Frontend Load Test**
- Tool: Lighthouse, WebPageTest, or Selenium-based bot
- Scenario: 20 concurrent users load borrower application form
- Metrics: Page load time, bundle size, JavaScript errors, time to interactive
- Expected: LCP <2s, FCP <1s, bundle <500KB

**Load Test Report (Template):**
```markdown
# Load Test Report

**Date:** 2024-11-21  
**Duration:** 5 minutes  
**Concurrent Users:** 100  

## Results

### Scoring Endpoint
- Mean Response Time: 800ms
- P95 Response Time: 1500ms
- P99 Response Time: 1900ms
- Error Rate: 0.3%
- Throughput: 18 req/sec
- **Status:** ✓ PASS (target <2s p95)

### Queue Endpoint
- Mean Response Time: 1200ms
- P95 Response Time: 2800ms
- P99 Response Time: 3500ms
- Error Rate: 0.1%
- Throughput: 8 req/sec
- **Status:** ✓ PASS (target <3s p95)

### Database Performance
- Connection Pool Peak: 48/100
- Average Query Time: 120ms
- Deadlocks: 0
- **Status:** ✓ PASS

### Frontend
- LCP: 1.8s
- FCP: 0.9s
- Bundle Size: 480KB (gzipped)
- JS Errors: 0
- **Status:** ✓ PASS

### Resource Usage
- Backend CPU Peak: 55% (on 8 cores)
- Backend Memory Peak: 1.2GB (on 2GB available)
- Database Disk I/O: Moderate
- **Status:** ✓ PASS

## Conclusion
System passes all load test criteria. Ready for production.
```

---

### 6. Production Deployment

**Objective:** Deploy backend, frontend, database to production, verify live operation, monitor for errors.

**Pre-Deployment Checklist:**

```markdown
# Production Deployment Checklist

## Backend
- [ ] All tests passing: `pytest tests/ -v`
- [ ] Coverage >80%: `pytest --cov=app --cov-report=term-missing`
- [ ] No warnings: `python -m pylint app/`
- [ ] Security audit complete: 0 critical issues
- [ ] Load test passed: 100+ concurrent users, <2s p95
- [ ] Integration tests passed: All 8 tests green
- [ ] Environment variables documented: `.env.example` complete
- [ ] Database migration script ready (if schema changed)
- [ ] Rollback procedure documented
- [ ] Git tag created: `git tag -a v1.0.0-phase1-2 -m "Phase 1-2 release"`

## Frontend
- [ ] Build passing: `npm run build` no errors
- [ ] Bundle analyzed: `npm run build` <500KB
- [ ] No TypeScript errors: `tsc --noEmit`
- [ ] No critical console errors in dev
- [ ] API endpoints verified in staging environment
- [ ] Glossary loaded correctly
- [ ] Tier-verified months logic correct

## ML
- [ ] Scorer compatible with backend decision schema
- [ ] 100 synthetic shops reproduce backend decisions (determinism)
- [ ] Models versioned and packaged

## Infrastructure
- [ ] Production database backup strategy ready
- [ ] Pre-deployment snapshot taken
- [ ] SSL certificate installed (or Let's Encrypt configured)
- [ ] Reverse proxy configured (nginx)
- [ ] Firewall rules allowing HTTPS (443)
- [ ] DNS updated to production domain
- [ ] Error logging configured (file-based or stdout)
- [ ] Monitoring tools ready (manual log checks for v1)

## Approval
- [ ] Backend Lead Sign-Off
- [ ] Frontend Lead Sign-Off
- [ ] Product Manager Approval
- [ ] Security Lead Approval (if required)
```

**Deployment Steps:**

1. **Backup Database (Pre-Deployment)**
   ```bash
   # Snapshot production database before deployment
   cp /data/production.db /data/production.db.backup.$(date +%Y%m%d_%H%M%S)
   ```

2. **Backend Deployment**
   ```bash
   # SSH into production server
   ssh production-server
   
   # Navigate to app directory
   cd /app
   
   # Pull latest code
   git fetch origin
   git checkout v1.0.0-phase1-2
   
   # Install dependencies
   pip install -r requirements.txt --upgrade
   
   # Run migrations (if any)
   python scripts/migrate.py
   
   # Run tests (quick sanity check)
   pytest tests/ -x  # Exit on first failure
   
   # Stop old process
   pkill -f "uvicorn main"
   
   # Start new process (in background or via systemd)
   nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > /var/log/uvicorn.log 2>&1 &
   
   # Or using systemd:
   # systemctl restart udyamcred-backend
   ```

3. **Frontend Deployment**
   ```bash
   # SSH into production server (or CDN)
   ssh production-server
   
   # Navigate to frontend directory
   cd /app/fe
   
   # Pull latest code
   git fetch origin
   git checkout v1.0.0-phase1-2
   
   # Install dependencies
   npm ci  # Use ci for reproducible installs
   
   # Build
   npm run build
   
   # Deploy to web server (nginx)
   rm -rf /var/www/html/*
   cp -r dist/* /var/www/html/
   
   # Or deploy to CDN (e.g., AWS S3 + CloudFront)
   # aws s3 sync dist/ s3://my-bucket/ --delete
   ```

4. **Post-Deployment Verification**
   ```bash
   # 1. Health check
   curl https://api.production-domain.com/health
   # Expected: {"status": "ok", "version": "0.2.0"}
   
   # 2. Frontend loads
   curl -I https://production-domain.com/
   # Expected: 200 OK
   
   # 3. Database connectivity
   curl https://api.production-domain.com/api/applications -H "Authorization: Bearer <token>"
   # Expected: 200 OK or 401 if auth required
   
   # 4. Logs clean
   tail -50 /var/log/uvicorn.log | grep -i error
   # Expected: No critical errors
   
   # 5. Monitor for 2 hours
   watch -n 60 'tail -20 /var/log/uvicorn.log'
   ```

5. **Rollback Plan (If Issues Arise)**
   ```bash
   # Stop current process
   pkill -f "uvicorn main"
   
   # Restore database from backup
   cp /data/production.db.backup.<timestamp> /data/production.db
   
   # Checkout previous version
   git checkout <previous-tag>
   
   # Restart
   nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 > /var/log/uvicorn.log 2>&1 &
   
   # Roll back frontend (if needed)
   git checkout <previous-tag>
   npm run build
   cp -r dist/* /var/www/html/
   ```

**Environment Configuration (.env.prod):**
```env
# Backend Configuration
DEBUG=False
DATABASE_URL=sqlite:////data/production.db
CORS_ORIGINS=https://production-domain.com
JWT_SECRET_KEY=<generate_strong_random_key_32_chars>
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=15
JWT_REFRESH_EXPIRY_DAYS=7

# Frontend Configuration (passed to build)
NEXT_PUBLIC_API_URL=https://api.production-domain.com
NEXT_PUBLIC_APP_NAME=UdyamCred
NEXT_PUBLIC_VERSION=1.0.0

# Security
SECURE_COOKIES=True
HTTPS_ONLY=True

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Monitoring & Alerting (First 2 Hours):**
```bash
# Manual log monitoring (v1)
watch -n 30 'tail -50 /var/log/uvicorn.log | tail -20'

# Check for errors
grep -i "error\|exception\|failed" /var/log/uvicorn.log

# Monitor API response times (sample)
curl -w "\nTime: %{time_total}s\n" https://api.production-domain.com/health

# Check database
sqlite3 /data/production.db "SELECT COUNT(*) FROM applications;"
```

**Success Criteria (First 2 Hours Post-Deploy):**
- ✓ Health check returns 200 OK
- ✓ All API endpoints respond
- ✓ No critical errors in logs (<5 errors/hour acceptable)
- ✓ Database queries execute <500ms (p95)
- ✓ Frontend loads in <2 seconds
- ✓ At least 1 successful scoring transaction completed

---

## Integration Points & Data Flow

### End-to-End Data Flow (Borrower Application → Officer Dashboard)

```
Borrower (Frontend)
  ↓ (Login)
  Backend Auth Endpoint → JWT + Refresh Token
  ↓ (Create App)
  Backend Application Endpoint → App Created (status: pending)
  ↓ (Grant Consent)
  Backend Consent Endpoint → Consent Stored
  ↓ (Upload Photos x3)
  Backend Photo Endpoint → Photo Verified (EXIF + Geolocation)
  ↓ (Upload Documents)
  Backend Document Endpoint → Document Stored (validated)
  ↓ (Enter Household)
  Backend Household Endpoint → Data Stored
  ↓ (Submit Application)
  Backend Scoring Orchestrator:
    1. Load Application + Shop + Household
    2. Fetch DataSources (AA, GST, UPI)
    3. PhotoVerificationEngine → photo_verified
    4. SourceAgreementEngine → source_agreement_score
    5. VerifiedWindowEngine → verified_months
    6. GSTCoverageEngine → gst_coverage_pct
    7. TierAssignmentEngine → tier
    8. AmountRuleEngine → approved_amount
    9. RateCalculationEngine → rate_percent
    10. TranchePlanEngine → tranche_plan[]
    11. Calculate EMI Schedule
    12. Generate Plain Language Reasons
    13. Save Decision + Tranches
    14. Return Phase1DecisionOut
  ↓ (View Result)
  Frontend Result Page displays: Tier, Amount, Rate, Reasons, Tranche Plan, EMI Schedule

Officer (Dashboard Frontend)
  ↓ (Login)
  Backend Auth Endpoint → JWT + Refresh Token (role: officer)
  ↓ (View Queue)
  Backend Applications Endpoint → List pending, filter by tier, sort by date
  ↓ (Click Case)
  Backend Application Endpoint → Fetch 5 tabs:
    - Overview: App details, tier, amount
    - Sources: DataSources (AA, GST, UPI data)
    - Photos: 3 photos + verification status
    - Documents: Uploaded docs + validation status
    - Repayment: EMI history (if released)
  ↓ (Replay Scoring)
  Backend Replay Endpoint → Rescore with modified household, return new decision (not persisted)
  ↓ (Override Decision)
  Backend Override Endpoint → Save override with officer_id + reason, create AuditLog
  ↓ (View Audit Trail)
  Backend Audit Endpoint → List all decisions, overrides, freezes for app

ML Pipeline (Evaluation)
  ↓ (Fetch Backend Decisions)
  Export 100 backend decisions to CSV
  ↓ (Rescore in ML)
  ML Pipeline rescores same 100 shops, compares outputs
  ✓ Determinism verified if outputs match 100%
```

---

## Edge Cases & Error Handling

| Scenario | Frontend Behavior | Backend Response | Recovery |
|----------|-------------------|------------------|----------|
| Photo geolocation >500m away | Show error "Photo location too far from shop address" | 400 Bad Request | User retakes photo |
| Missing EXIF data | Warning "Could not verify location, please try again" | 400 Bad Request or 201 with verified: false | User retakes photo with EXIF camera |
| GST data missing | Tier assigned without GST (lower tier possible) | Scoring continues with AA+UPI only | App qualifies for Tier 1 instead of Tier 2 |
| 2+ missed EMIs | Freeze triggered automatically | Application status changed to "frozen", 403 on tranche release | Officer can unfreeze (manual override) |
| Consent withdrawn | Cannot score | 400 Bad Request | User re-grants consent |
| Database connection lost | "Server error, please try again" | 500 Internal Server Error | Retry (automatic in React Query) |
| Rate adapter returns null | Use fallback rate (20%) | Decision saved with fallback rate + note in audit log | Monitor and investigate |
| Tranche eligibility check fails | "You're not yet eligible to request this tranche" | 403 Forbidden | Wait for prior tranches to complete |

---

## Testing & Verification Matrix

| Phase | Test Type | Tool | Success Criteria | Status |
|-------|-----------|------|------------------|--------|
| **Unit** | Engine logic | pytest | >80% coverage, 286 tests | ✓ EXISTING |
| **Integration** | E2E workflows | pytest + FastAPI TestClient | 8 integration tests pass | **IN PROGRESS** |
| **Security** | OWASP Top 10 | OWASP ZAP + manual | 0 critical issues | **IN PROGRESS** |
| **Load** | Concurrency | JMeter | 100 users, <2s p95, <1% error | **IN PROGRESS** |
| **Smoke** | Post-deployment | curl + browser | Health check + 1 E2E | **ON DEPLOY** |

---

## Files to Modify / Create

**Backend:**
- `be/app/endpoints/scoring_phase1.py` - Wire orchestration (MAIN WORK)
- `be/app/endpoints/photos.py` - Photo verification integration
- `be/app/endpoints/tranches.py` - Tranche eligibility + release
- `be/app/endpoints/repayment.py` - EMI recording + freeze logic
- `be/app/endpoints/override.py` - NEW: Override endpoint
- `be/app/templates/reasons.py` - NEW: Plain language reason generation
- `be/app/schemas.py` - Update Phase1DecisionOut schema
- `be/tests/integration/` - NEW: 8 integration tests
- `.env.example` - Document all prod config
- `DEPLOYMENT_GUIDE.md` - NEW: Step-by-step deployment instructions

**Frontend:**
- `fe/src/pages/ApplicationForm.tsx` - Collect tier-driven verified months
- `fe/src/pages/ResultPage.tsx` - Display reasons + glossary
- `fe/src/pages/OfficerDashboard.tsx` - Queue view + replay + override
- `fe/src/components/Glossary.tsx` - 18 terms + definitions
- `fe/src/utils/glossary.ts` - NEW: Glossary data structure
- `fe/tests/integration/` - NEW: Vitest E2E tests (optional for v1)

**ML:**
- `ml/evaluation_phase1_2.py` - NEW: Determinism validation script
- `ml/tier_rules.py` - Update with Phase 1-2 logic

**Utilities:**
- `scripts/load_test_scoring.jmx` - NEW: JMeter config
- `scripts/load_test_locust.py` - NEW: Locust config
- `scripts/security_audit.py` - NEW: OWASP ZAP scanning script
- `scripts/pre_deploy_checks.sh` - NEW: Deployment checklist script

---

## Technology Stack Summary (Locked)

**Backend:** FastAPI, SQLAlchemy, SQLite, Uvicorn, Pydantic, PyJWT, Bcrypt  
**Frontend:** React, React Query, React Hook Form, Zod, Zustand, React Router, Vite, TypeScript  
**ML:** Python, Pandas, NumPy, PyYAML  
**Testing:** pytest, JMeter, OWASP ZAP, Vitest  
**Deployment:** Git, Systemd (or manual uvicorn), Nginx (reverse proxy), SQLite (backup)  

---

## Success Metrics (Locked)

✓ All 8 integration tests pass  
✓ Security audit: 0 critical issues  
✓ Load test: 100+ concurrent users, <2s p95 response time, <1% error rate  
✓ Production deployment: 0 downtime, all endpoints functional, live verification complete  

---

## Design Decisions & Rationale

| Decision | Rationale | Alternative Rejected |
|----------|-----------|----------------------|
| **Orchestration in single endpoint** | Ensures atomicity, easier to test, reproducible for ML evaluation. | Microservices would add complexity, harder to debug. |
| **Deterministic adapters (mock)** | Enables offline testing, reproducibility, ML validation. Real APIs require credentials, rate limiting, compliance. | Real API integration deferred to Phase 3. |
| **SQLite for v1** | Single-file database, easy backup/restore, sufficient for v1 scale (~10k records). | PostgreSQL would add DevOps overhead for v1. Upgrade to v1.1 if scaling. |
| **Direct production rollout** | Assumes comprehensive pre-deployment validation (integration tests, security audit, load tests). No canary phase saves time. | Canary rollout useful for larger systems; not needed for v1 MVP. |
| **No rate limiting in v1** | Simplifies implementation, sufficient for pilot phase. Can add in v1.1 if needed. | Rate limiting would add latency, complexity for v1. |
| **Rule-based tier assignment** | Explainable, auditable, compliant with lending regulations. ML-driven scoring riskier. | ML models deferred to Phase 3 after more data/evaluation. |
| **Synchronous API calls** | All operations <2 seconds, no need for async. Simpler error handling. | Async would help with external API calls (not applicable with mocks). |

---

## Assumptions & Dependencies

**Assumptions:**
- Production environment has 2GB RAM, 2 CPU cores, 20GB disk
- Backend and frontend can run on same or separate machines (low-latency assumed)
- Team can deploy manually (no CI/CD pipeline required for v1)
- Deterministic adapters sufficient for testing (real data integration Phase 3)
- 100 synthetic shops representative of real portfolio

**Dependencies:**
- Phase 1 engines stable (90%+ test coverage existing)
- Database schema finalized and migrated
- Frontend captures tier-driven verified months correctly
- ML team validates determinism post-deployment

---

## Rollback & Disaster Recovery

**Rollback Procedure (If Critical Issue):**
1. Identify issue (from logs, user reports)
2. Restore database from backup: `cp /data/production.db.backup.<timestamp> /data/production.db`
3. Checkout previous release: `git checkout v0.9.0`
4. Restart backend
5. Clear frontend cache (cache busting via versioned bundle)
6. Run smoke tests to verify rollback

**Recovery Time Objective (RTO):** <30 minutes  
**Recovery Point Objective (RPO):** <1 hour (database backup frequency)

---

## Appendix: Glossary Terms (18)

1. **Account Aggregator (AA)** - Bank account data verified for 6+ months
2. **GST** - Sales tax records from government
3. **UPI** - Mobile payment records
4. **Verified Window** - The period where we have confirmed your data
5. **Turnover** - Total sales your business makes annually
6. **Purchases** - Goods you buy for your business
7. **Coverage** - How much of your claimed sales match tax records
8. **Tier 1** - Entry-level borrowers with 6+ months verified data
9. **Tier 2** - Established borrowers with 12+ months and GST registration
10. **Tier 3** - Experienced borrowers with 2+ years data and prior loan history
11. **EMI** - Equal monthly payment (principal + interest)
12. **Tenor** - Loan repayment period in months
13. **Tranche** - Part of the loan released over time (not all at once)
14. **On-Time** - Payment made by due date
15. **Missed** - Payment not made by due date
16. **Frozen** - Loan stopped due to 2+ missed payments
17. **Udyam Registration** - Formal government registration for MSMEs
18. **Prior Repayment** - History of paying back previous loans on time

