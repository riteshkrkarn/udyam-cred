# Stage 2 Implementation Plan - UdyamCred Backend (MVP)

## Checkpoint

**A borrower applies, adds documents/manual entries, and gets a decision with amount, rate, EMI schedule, reasons and a recommended fund plan. A bank officer sees the decision, changes an input in the replay view, and overrides with a reason. The override is recorded.**

## Overview

Stage 2 builds the end-to-end API and business logic for:
1. **Borrower journey:** Apply → Consent → Enter data (documents or manual) → Household budget → Get decision with loan amount, rate, EMI
2. **Officer workflow:** Review application queue → View decision → Replay (change inputs) → Override with reason
3. **Backend engines:** ABCA estimator, vintage engine, household surplus calculation, capacity model, loan amount rule, rate band rule, EMI calculation, fund split optimizer
4. **Storage:** Consent tracking, decisions with reasons, overrides with audit trail

## Architecture

Layered approach (continues from Stage 1):

```
API Layer (main.py, endpoints)
├── /applications/* (create, list, get, update status)
├── /scoring/* (score, replay, audit)
├── /decisions/* (decisions by application, override)
├── /documents/* (upload, list)
├── /auth/* (login, refresh, logout)
└── /health (status check)

Business Logic Layer (app/engines/*.py)
├── abca_engine.py - ABCA estimator (two sources: UPI, Account Aggregator)
├── vintage_engine.py - Earliest supported date from two sources
├── round_trip_engine.py - Detect circular money patterns
├── capacity_engine.py - Repayment capacity model
├── loan_rules_engine.py - Apply policy caps, stock limits
├── rate_engine.py - Map risk band to ROI, tenor to rate
├── emi_engine.py - Calculate EMI schedule, household surplus
├── fund_split_engine.py - Recommend stock/buffer/expansion/reserve split

Data Layer (app/models.py, database.py)
├── Extended models for Stage 2
├── Application, Consent, Decision, Override, Document models
└── Audit trail tables

External Adapters (app/adapters/*.py)
├── upi_adapter.py - Mock UPI data fetch
├── account_aggregator_adapter.py - Mock AA data fetch
├── gst_registry_adapter.py - Mock GST data fetch
```

## Tasks

### Task 1: Extended Database Schema and Models

**Objective:** Add models for applications, consent, documents, decisions, overrides, audit logs.

**Files to create/modify:**
- `app/models.py` - Add:
  - `Application` (borrower_id, shop_id, loan_amount_requested, purpose, status: pending/approved/rejected, created_at)
  - `Consent` (application_id, text, borrower_agreed, agreed_at, withdrawn_at)
  - `Document` (application_id, document_type: bill/purchase/ledger, file_path, uploaded_at)
  - `HouseholdData` (application_id, family_size, dependents, monthly_expenses, assets, liabilities)
  - `Decision` (application_id, verdict: approved/rejected, loan_amount, rate, emi_monthly, confidence, reasons_json, created_at, replay_count)
  - `Override` (decision_id, officer_id, old_loan_amount, new_loan_amount, reason, created_at)
  - `AuditLog` (entity_type: application/decision/override, entity_id, action: created/updated/overridden, officer_id, timestamp)
  - `DataSource` (application_id, source: upi/aa/gst, vintage_date, data_json)

**Tests:**
- Model relationships and constraints
- Cascade deletes
- Audit log triggers

**Demo:** All new models create, update, query without errors.

---

### Task 2: External Data Adapters (Mock)

**Objective:** Create mock adapters for UPI, Account Aggregator, GST registry.

**Files to create:**
- `app/adapters/base.py` - Abstract adapter interface
- `app/adapters/upi_adapter.py` - Fetch mock UPI transactions (daily UPI inflows for last 12 months)
- `app/adapters/account_aggregator_adapter.py` - Fetch mock bank/ledger data (monthly opening/closing balance, turnover)
- `app/adapters/gst_adapter.py` - Fetch mock GST data (turnover, monthly filings)

**Each adapter returns:**
- `{vintage_date, data_hash, transactions/summary}`

**Tests:**
- Each adapter returns valid data schema
- Errors handled gracefully
- Data is deterministic for test shopids

**Demo:** 
```python
upi_data = get_upi_data(shop_id=1)  # Returns 12 months of daily UPI
aa_data = get_aa_data(shop_id=1)    # Returns 12 months of bank data
gst_data = get_gst_data(gstin="27AAGPT7202F1Z5")  # Returns turnover
```

---

### Task 3: ABCA Engine (Average Bank Credit Aggregator)

**Objective:** Estimate Average Bank Credit Available from two sources (UPI + Account Aggregator).

**Files to create:**
- `app/engines/abca_engine.py`

**Logic:**
- UPI source: Sum 12 months UPI inflows, divide by 12 (average monthly UPI)
- AA source: Sum 12 months bank deposits, divide by 12 (average monthly bank)
- ABCA = (UPI_avg + AA_avg) / 2
- If either source missing, use single source
- Return: {abca_value, upi_avg, aa_avg, confidence, vintage_dates}

**Tests:**
- Single source (UPI only, AA only)
- Both sources available
- Missing data handling
- Confidence calculation (agree = high confidence, differ = medium)

---

### Task 4: Vintage Engine

**Objective:** Determine earliest supported date from two sources.

**Files to create:**
- `app/engines/vintage_engine.py`

**Logic:**
- Input: UPI vintage date, AA vintage date
- Output: {earliest_date, supporting_sources_count}
- Only loan for months where both sources agree (or single source if one missing)

**Tests:**
- Both dates same
- One source older
- One source missing

---

### Task 5: Round-Trip Detection (Simple)

**Objective:** Flag circular money patterns.

**Files to create:**
- `app/engines/round_trip_engine.py`

**Logic:**
- Simple version (Stage 2): Check for patterns like:
  - Same counterparty appearing on multiple UPI transactions in short windows
  - Large transfers out followed by similar transfers in
  - Score from 0 (no round-trip) to 1 (high confidence round-trip)

**Output:** {score, flagged_transactions, confidence}

**Tests:**
- Clean transaction history (score = 0)
- Circular pattern detected (score > 0.5)

---

### Task 6: Household Data and Surplus Calculation

**Objective:** Collect household budget, calculate surplus available for EMI.

**Files to create:**
- `app/engines/emi_engine.py`

**Logic:**
- Input: family_size, monthly_expenses, existing_liabilities
- Monthly household surplus = (ABCA + other_income) - monthly_expenses - existing_emi
- EMI capacity = surplus * emi_share (default 0.5 from policy)
- Return: {household_surplus, emi_capacity, monthly_surplus_after_emi}

**Tests:**
- Typical household
- High expenses (low surplus)
- Edge cases (zero surplus)

---

### Task 7: Repayment Capacity Model

**Objective:** Predict safe repayment amount using trained model (from ML team or baseline).

**Files to create:**
- `app/engines/capacity_engine.py`

**Logic:**
- Load pre-trained capacity model (pickle/joblib from ml/ folder)
- Input: {goods_sold, margin, family_size, liabilities, round_trip_score, vintage_months}
- Output: {safe_amount, confidence, capacity_used_percent}

For MVP, use a simple rule-based fallback:
- `safe_amount = ABCA * 0.5 * (1 - round_trip_risk)` if model missing

**Tests:**
- Model inference works
- Fallback rule works
- Output bounds (0 to policy cap)

---

### Task 8: Loan Amount Rule Engine

**Objective:** Determine approved loan amount (lowest of three constraints).

**Files to create:**
- `app/engines/loan_rules_engine.py`

**Logic:**
```
loan_amount = min(
    emi_capacity,           # From household surplus
    safe_amount,            # From capacity model
    policy_cap              # From policy.yaml
)
```

If any constraint is 0 or negative, reject application.

**Tests:**
- All constraints apply
- One constraint is binding
- Rejection logic

---

### Task 9: Rate Band Rule Engine

**Objective:** Map risk band to interest rate based on tenor.

**Files to create:**
- `app/engines/rate_engine.py`

**Logic:**
- Determine risk band from scorecard (Low/Moderate/High/Needs Review)
  - For MVP: Use simple rule: `band = "Moderate"` (placeholder until scorecard ready)
- Look up rate from policy: `rate_bands[band][tenor]`
- Return: {rate_percent, band, tenor_months}

**Tests:**
- Each risk band returns valid rate
- Tenor interpolation/lookup

---

### Task 10: EMI Schedule Calculation

**Objective:** Generate EMI schedule for given loan amount, rate, tenor.

**Files to create:**
- `app/engines/emi_engine.py` (extend from Task 6)

**Logic:**
- Standard EMI formula: `emi = (P * r * (1+r)^n) / ((1+r)^n - 1)`
  - P = principal (loan amount)
  - r = monthly rate (annual_rate / 12 / 100)
  - n = number of months
- Return: [{month, principal, interest, balance}, ...]

**Tests:**
- Standard 12-month loan
- 24-month, 36-month
- Verify total interest, final balance = 0

---

### Task 11: Fund Split Optimizer

**Objective:** Recommend split of loan across stock, buffer, expansion, reserve.

**Files to create:**
- `app/engines/fund_split_engine.py`

**Logic:**
- Input: {loan_amount, goods_sold, margin, category, monthly_turnover}
- Calculate:
  - Stock: goods_sold * buffer_months / (1 + margin)
  - Buffer: stock * 0.2 (20% buffer for slow-moving items)
  - Expansion: loan_amount * 0.2 (20% for growth)
  - Reserve: remaining
- Return: {stock_percent, buffer_percent, expansion_percent, reserve_percent, recommendations}

**Tests:**
- Typical kirana shop
- High-margin vs low-margin categories

---

### Task 12: Scoring Endpoint

**Objective:** Orchestrate all engines to score an application and generate decision.

**Files to create:**
- `app/endpoints/scoring.py` (new router)

**Endpoint:** `POST /api/scoring/score`

**Input:**
```json
{
  "application_id": "app_123",
  "shop_id": "shop_1",
  "family_size": 4,
  "monthly_expenses": 25000,
  "existing_liabilities": 50000,
  "tenor_months": 12
}
```

**Orchestration:**
1. Fetch ABCA (via adapters)
2. Run vintage engine
3. Calculate household surplus
4. Get safe amount (capacity model)
5. Apply loan amount rule
6. Determine rate band
7. Calculate EMI schedule
8. Optimize fund split
9. Generate reason codes
10. Save decision, return result

**Output:**
```json
{
  "decision_id": "dec_456",
  "verdict": "approved",
  "loan_amount": 75000,
  "rate_percent": 12.5,
  "emi_monthly": 6850,
  "emi_schedule": [...],
  "fund_plan": {
    "stock_percent": 50,
    "buffer_percent": 10,
    "expansion_percent": 20,
    "reserve_percent": 20
  },
  "confidence": 0.82,
  "reasons": ["stable cash flow", "good vintage", "positive household surplus"],
  "abca": 85000,
  "household_surplus": 35000,
  "safe_amount": 90000
}
```

**Tests:**
- Happy path (all engines work)
- Partial data (missing AA, use UPI only)
- Rejection cases

---

### Task 13: Replay Engine

**Objective:** Re-score application with modified inputs (for officer review).

**Endpoint:** `POST /api/scoring/replay`

**Input:**
```json
{
  "decision_id": "dec_456",
  "overrides": {
    "family_size": 5,
    "monthly_expenses": 30000
  }
}
```

**Logic:**
- Load original decision
- Apply overrides to inputs
- Re-run scoring engines
- Return new decision WITHOUT saving
- Track replay_count on original decision

**Tests:**
- Valid override
- Invalid override (negative values)
- Multiple replays

---

### Task 14: Override Workflow

**Objective:** Officer can override decision with reason.

**Endpoint:** `POST /api/scoring/override`

**Input:**
```json
{
  "decision_id": "dec_456",
  "new_loan_amount": 50000,
  "reason": "Customer requested lower amount for conservative cash flow"
}
```

**Logic:**
1. Load decision
2. Validate new amount (not exceeding capacity)
3. Create Override record (officer_id from token)
4. Log to AuditLog
5. Return updated decision

**Tests:**
- Valid override
- Override exceeding capacity (error)
- Audit trail created

---

### Task 15: Application Endpoints

**Objective:** Full CRUD for applications.

**Endpoints:**
- `POST /api/applications` - Create new application
- `GET /api/applications/{id}` - Get application details
- `GET /api/applications?status=pending` - List (filter by status)
- `PATCH /api/applications/{id}` - Update status (submitted, reviewed, etc.)

**Tests:**
- Create, read, update, filter
- Permissions (owner can only access own apps)

---

### Task 16: Consent Management

**Objective:** Store borrower consent.

**Endpoint:** `POST /api/applications/{id}/consent`

**Input:**
```json
{
  "agreed": true,
  "consent_text": "I agree to share my UPI and bank data..."
}
```

**Logic:**
- Create Consent record (agreed_at timestamp)
- Mark application as consent_received
- Can later call `DELETE /api/applications/{id}/consent` to withdraw

**Tests:**
- Consent given
- Consent withdrawn
- Cannot score without consent

---

### Task 17: Document Upload

**Objective:** Store documents (purchases bills, bank statements, etc.).

**Endpoint:** `POST /api/applications/{id}/documents`

**Input:** multipart form with file + metadata

**Logic:**
- Save file to `data/documents/{app_id}/{doc_type}/`
- Record Document model with file_path, doc_type
- Validate file type (pdf, jpg, png)
- Scan for PII (optional, Stage 3)

**Tests:**
- Upload valid file
- Reject invalid type
- Document retrieval

---

### Task 18: Household Data Collection

**Endpoint:** `POST /api/applications/{id}/household`

**Input:**
```json
{
  "family_size": 4,
  "dependents": 2,
  "monthly_expenses": 25000,
  "assets": 200000,
  "liabilities": 50000
}
```

**Logic:**
- Create/update HouseholdData record
- Validate ranges (family_size > 0, expenses > 0)
- Return calculated surplus

**Tests:**
- Valid household data
- Invalid data rejection

---

### Task 19: Audit View

**Objective:** List decisions and overrides with full audit trail.

**Endpoint:** `GET /api/audit/decisions?application_id=...&date_range=...`

**Logic:**
- Return decisions with replay_count, override_count
- Include all overrides with reasons
- Officer/auditor role required

**Tests:**
- Audit data complete
- Permissions enforced

---

### Task 20: Integration Tests

**Objective:** End-to-end application flow.

**Tests:**
- Borrower creates application
- Consent given
- Household data entered
- Scoring runs (all engines)
- Decision returned
- Officer replays with changes
- Officer overrides with reason
- Audit trail complete

---

### Task 21: Error Handling and Validation

**Objective:** Comprehensive error handling across all endpoints.

**Implement:**
- Input validation (Pydantic schemas)
- HTTP error responses (400 bad request, 403 forbidden, 404 not found, 500 server error)
- Logging of all errors
- User-friendly error messages

**Tests:**
- Invalid input
- Missing required fields
- Unauthorized access
- Not found

---

### Task 22: Tests and Coverage

**Objective:** Full test suite for Stage 2.

**Create:**
- `tests/test_abca_engine.py`
- `tests/test_vintage_engine.py`
- `tests/test_round_trip_engine.py`
- `tests/test_capacity_engine.py`
- `tests/test_loan_rules_engine.py`
- `tests/test_rate_engine.py`
- `tests/test_emi_engine.py`
- `tests/test_fund_split_engine.py`
- `tests/test_scoring_endpoint.py`
- `tests/test_replay_engine.py`
- `tests/test_override_workflow.py`
- `tests/test_applications_endpoints.py`
- `tests/test_consent.py`
- `tests/test_documents.py`
- `tests/test_household.py`
- `tests/test_audit.py`
- `tests/test_integration_e2e.py`

**Coverage target:** >85% for all new code.

---

## Implementation Order

1. **Tasks 1-2:** Models and adapters (foundation)
2. **Tasks 3-11:** All engines (business logic)
3. **Tasks 12-19:** Endpoints (API layer)
4. **Tasks 20-22:** Integration and tests

## Key Design Principles

- **Deterministic:** Same inputs always produce same outputs (testable, debuggable)
- **Auditable:** Every decision tracked with reasons, every override logged
- **Extensible:** Engines decoupled so Stage 3 can add more sources, models
- **Robust:** Graceful fallbacks when data missing (UPI only if AA missing, etc.)
- **Testable:** Mock adapters allow offline testing

## Deliverables

- ✅ Full end-to-end application flow
- ✅ All 8 business logic engines
- ✅ Complete API (borrower + officer workflows)
- ✅ Decision with reasons, EMI schedule, fund plan
- ✅ Replay and override functionality
- ✅ Audit trail
- ✅ >150 integration + unit tests
- ✅ >85% code coverage

## Stage 2 Checkpoint

A complete borrower journey: Apply → Consent → Household data → Score → Get decision with loan amount, rate, EMI, fund plan. Officer can review, replay, override. All decisions audited.
