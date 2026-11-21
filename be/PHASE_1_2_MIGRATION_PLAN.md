# Two-Phase Migration Plan: Stage 2 → Tiered Verification-First System

## Overview

Transform the current generic credit scoring system (Stage 2) into a **verification-first, photo-evidence, tiered-lending product** with multi-tranche gates and industry-rate-based ROI.

**Key Principle:** Trust only sources the owner cannot edit (AA bank data, GST filings, geo-tagged photos). Owner bills = weak evidence only.

---

## Phase 1: Foundation (Weeks 1-2)

Build the core data model, engines, and basic workflows. At the end of Phase 1, the system can:
- Assign borrowers to Tier 1, 2, or 3 based on verified data
- Generate multi-tranche loan plans
- Collect and verify geo-tagged photos
- Track repayment and enforce stop rules

**Effort:** ~5 days

### Phase 1 Tasks

#### 1.1 Database Schema Refactor
**File:** `app/models.py`

**Add tables:**
- `Tier` (tier_id, name, min_verified_months, min_amount, max_amount, rate_adjustment, confidence_threshold)
- `Photo` (application_id, photo_type: shop_front/shelves/bills/rent_receipt/udyam/gst, photo_path, location_lat, location_lng, timestamp, random_code_written, verification_status, verified_at)
- `SourceAgreement` (application_id, upi_monthly_avg, aa_monthly_avg, gst_monthly_avg, agreement_score_percent)
- `VerifiedWindow` (application_id, start_date, end_date, months_verified, data_quality_score, weighted_importance)
- `GSTCoverage` (application_id, purchases_declared, gst_turnover, coverage_percent, reconciliation_flag)
- `Tranche` (application_id, tranche_num, amount, release_date, release_status: pending/released/repaid, emi_count, tenor_months)
- `RepaymentRecord` (tranche_id, emi_num, due_date, amount, paid_date, payment_status: ontime/late/missed/bounced, days_late)
- `StopRule` (application_id, missed_emi_count, frozen_date, review_required, unfrozen_date)
- `LocationVerification` (application_id, rent_address, shop_address, photo_location_lat, photo_location_lng, distance_meters, verified_bool)
- `RateEnvironment` (rate_date, tier_1_industry_rate, tier_2_industry_rate, tier_3_industry_rate, source: "manual" or "api")

**Modify:**
- `Decision`: Replace `loan_amount, rate_percent, emi_monthly` with `tier, verified_months, source_agreement_score, location_verified, photo_count, tranche_plan_json`
- Drop: `confidence` (different meaning now)

**Remove/Deprecate:**
- `Decision.risk_band`
- Capacity model references

**Tests:** Model creation, relationships, cascade deletes, constraints

**Demo:** All new tables create/query without errors; foreign keys enforced

---

#### 1.2 Data Adapters: Industry Rate Lookup
**File:** `app/adapters/rate_adapter.py` (new)

**Functionality:**
- Fetch current industry rates for MSME loans by tier
- Sources: Manual entry (admin), or API call to rate provider (RBI, financial platforms)
- Store in `RateEnvironment` table

**Interface:**
```python
def get_industry_rate(tier: int) -> float:
    # Returns: 14.5 (for Tier 1), 12.0 (for Tier 2), 10.5 (for Tier 3)
    # This is the base rate; actual rate = base + adjustment from policy

def set_industry_rates(tier_1: float, tier_2: float, tier_3: float, source: str):
    # Admin endpoint to update rates
```

**Tests:** Rate fetch, update, default fallback rates

**Demo:** `get_industry_rate(1)` returns ₹14.5, `get_industry_rate(2)` returns ₹12.0

---

#### 1.3 Photo Verification Engine
**File:** `app/engines/photo_verification_engine.py` (new)

**Functionality:**
- Validate photo contains written random code
- Extract geolocation from EXIF/metadata
- Compare photo location to rent agreement address
- Flag suspicious photos (too old, location mismatch, code unreadable)

**Input:**
```python
{
  "photo_file": binary,
  "expected_code": "ABC123",
  "rent_address": "123 Main St, Bangalore",
  "tolerance_meters": 500
}
```

**Output:**
```python
{
  "code_verified": true/false,
  "location_verified": true/false,
  "location_lat": 12.9716,
  "location_lng": 77.5946,
  "location_confidence": 0.95,
  "distance_from_rent": 120,
  "issues": []
}
```

**Tests:** Valid photo, missing code, location mismatch, invalid format

**Demo:** Upload photo with code + location, verify both are captured

---

#### 1.4 Source Agreement Engine (Replace ABCA)
**File:** `app/engines/source_agreement_engine.py` (replaces `abca_engine.py`)

**Functionality:**
- Compare monthly sales from three sources: AA bank, GST filings, UPI
- AA bank data = primary (owner cannot edit)
- GST filings = secondary (owner cannot edit)
- UPI = tertiary (owner cannot edit, but less reliable)
- Output: agreement score (0-100%), weighted average sales

**Input:**
```python
{
  "application_id": "app_123",
  "aa_monthly_avg": 80000,  # From Account Aggregator
  "gst_monthly_avg": 85000,  # From GST filings (if registered)
  "upi_monthly_avg": 120000  # From UPI data
}
```

**Output:**
```python
{
  "weighted_sales": 82500,  # Weighted by source reliability
  "aa_weight": 0.6,
  "gst_weight": 0.3,
  "upi_weight": 0.1,
  "agreement_score": 0.82,  # How well sources agree (0-1)
  "sources_used": ["aa", "gst"],
  "confidence": "medium"  # low/medium/high based on agreement
}
```

**Logic:**
- If all 3 sources available: agreement_score = correlation(sources)
- If 2 sources: correlation(aa, gst) weighted 60/40
- If 1 source (UPI only): score = 0.5 (weak confidence)
- Weighted sales = (aa_avg × 0.6) + (gst_avg × 0.3) + (upi_avg × 0.1)

**Tests:** Single source, two sources, all three; agreement calculation

---

#### 1.5 Verified Window Engine
**File:** `app/engines/verified_window_engine.py` (new)

**Functionality:**
- Calculate months where multiple sources overlap (verified data)
- Only months with AA + (GST or UPI) count
- Score data quality by consistency over the window
- Longer window = higher weight for amount calculation

**Input:**
```python
{
  "aa_start": "2024-01-01",
  "aa_end": "2024-12-31",
  "gst_start": "2024-03-01",
  "gst_end": "2024-12-31",
  "upi_start": "2024-01-01",
  "upi_end": "2024-12-31"
}
```

**Output:**
```python
{
  "window_start": "2024-03-01",
  "window_end": "2024-12-31",
  "months_verified": 10,
  "data_quality_score": 0.85,  # How consistent/clean
  "weight_factor": 0.83  # For amount scaling (10 months / 12 max)
}
```

**Tests:** Various data ranges, missing sources, edge cases (< 6 months)

---

#### 1.6 GST Coverage Engine
**File:** `app/engines/gst_coverage_engine.py` (new)

**Functionality:**
- Compare purchases declared on bills to GST turnover reported
- Flag discrepancies (may indicate unreported sales or bill inflation)
- Coverage % = GST turnover / purchases

**Input:**
```python
{
  "purchases_from_bills": 500000,  # From uploaded bills
  "gst_turnover": 520000  # From GSTR-2B filing
}
```

**Output:**
```python
{
  "coverage_percent": 1.04,  # 104% (good alignment)
  "reconciliation_flag": false,
  "notes": "GST filing aligns well with purchases"
}
```

**Tests:** Good alignment, high discrepancy, missing GST

---

#### 1.7 Tier Assignment Engine
**File:** `app/engines/tier_assignment_engine.py` (new)

**Functionality:**
- Assign borrower to Tier 1, 2, or 3 based on verified data
- Return reasons for tier assignment
- Return next-tier qualification criteria

**Tier Rules:**
- **Tier 1:** 6+ months AA + UPI, no GST, no Udyam, source agreement > 0.7, photo verified
  - Amount cap: ₹50,000, single tranche, tenure 12 months
  - Rate: Industry rate + 4%
  
- **Tier 2:** 12+ months (AA + GST), or 12+ months AA + UPI with GST registered, no Udyam
  - Amount cap: ₹250,000, 2-3 tranches, tenure 24 months
  - Rate: Industry rate + 2%
  
- **Tier 3:** 24+ months AA + GST, Udyam registered, prior repayment record with us
  - Amount cap: ₹1,000,000, 4+ tranches, tenure 36 months
  - Rate: Industry rate + 0%

**Input:**
```python
{
  "verified_months": 10,
  "source_agreement_score": 0.82,
  "photo_verified": true,
  "gst_registered": false,
  "udyam_registered": false,
  "prior_repayment_history": null  # Only for existing customers
}
```

**Output:**
```python
{
  "tier": 1,
  "max_amount": 50000,
  "rate_adjustment": 4.0,  # Add to industry rate
  "tranche_plan": "single",  # or "2-3" or "4+"
  "tenure_months": 12,
  "reasons": [
    "Verified 10 months of bank data (requires 6+)",
    "AA and UPI agree on sales 82%",
    "Shop location verified with rent agreement",
    "Not registered for GST (Tier 2 requires it)"
  ],
  "next_tier_criteria": [
    "Register for GST to qualify for Tier 2",
    "Maintain 6+ months of on-time repayment",
    "Increase verified history to 12 months"
  ]
}
```

**Tests:** All tier assignments, edge cases (exactly 6 months, just under)

---

#### 1.8 Amount Rule Engine (Replace Loan Rules)
**File:** `app/engines/amount_rule_engine.py` (replaces `loan_rules_engine.py`)

**Functionality:**
- Calculate approved loan amount based on tier, verified window, source agreement
- Apply scaling factors: verification weight, agreement weight, policy cap

**Input:**
```python
{
  "tier": 1,
  "verified_months": 10,
  "source_agreement_score": 0.82,
  "gst_coverage": 1.04,  # GST/purchases ratio
  "weighted_sales": 85000
}
```

**Calculation:**
```
tier_cap = TIER_CAPS[tier]  # e.g., 50,000 for Tier 1
verified_weight = min(verified_months / TIER_MIN_MONTHS[tier], 1.0)
  # e.g., 10/6 = 1.67, capped at 1.0
agreement_weight = source_agreement_score
  # e.g., 0.82

amount = tier_cap × verified_weight × agreement_weight
       = 50,000 × 1.0 × 0.82
       = 41,000
```

**Output:**
```python
{
  "approved_amount": 41000,
  "tier_cap": 50000,
  "verified_weight": 1.0,
  "agreement_weight": 0.82,
  "reasoning": "Tier 1 cap ₹50K, scaled by agreement 82%"
}
```

**Tests:** Various tier/verification/agreement combinations

---

#### 1.9 Rate Calculation Engine (New)
**File:** `app/engines/rate_calculation_engine.py` (new)

**Functionality:**
- Fetch industry rate for tier
- Apply tier-based adjustment from policy
- Calculate final APR

**Input:**
```python
{
  "tier": 1,
  "rate_date": "2024-11-20"
}
```

**Output:**
```python
{
  "industry_rate": 14.5,  # Base MSME rate
  "tier_adjustment": 4.0,  # + 4% for Tier 1
  "final_rate": 18.5,  # 14.5 + 4.0
  "rate_date": "2024-11-20"
}
```

**Tests:** Rate fetch, adjustment application, date handling

---

#### 1.10 Tranche Plan Generator
**File:** `app/engines/tranche_plan_engine.py` (new)

**Functionality:**
- Generate multi-tranche release schedule based on tier and amount
- Apply fixed release intervals (e.g., every 60 days for Tier 2)

**Input:**
```python
{
  "tier": 2,
  "amount": 200000,
  "start_date": "2024-11-20"
}
```

**Output:**
```python
{
  "tranche_plan": [
    {"tranche_num": 1, "amount": 120000, "release_date": "2024-11-20"},
    {"tranche_num": 2, "amount": 80000, "release_date": "2025-01-20"}
  ],
  "total_amount": 200000,
  "tenure_months": 24
}
```

**Tranche Logic by Tier:**
- **Tier 1:** 1 tranche (100% now)
- **Tier 2:** 2-3 tranches (60% now, 40% at +60d)
- **Tier 3:** 4 tranches (40% now, 30% at +60d, 20% at +120d, 10% at +180d)

**Tests:** Tranche generation for each tier

---

#### 1.11 Tranche Rule Engine
**File:** `app/engines/tranche_rule_engine.py` (new)

**Functionality:**
- Determine if next tranche is eligible based on repayment history
- Require all previous tranches' EMIs to be on-time

**Input:**
```python
{
  "application_id": "app_123",
  "tranche_num": 2,
  "repayment_records": [
    {"emi_num": 1, "status": "ontime"},
    {"emi_num": 2, "status": "ontime"},
    {"emi_num": 3, "status": "ontime"}
  ]
}
```

**Output:**
```python
{
  "eligible": true,
  "reason": "All EMIs from tranche 1 paid on-time",
  "release_date": "2025-01-20"
}
```

**Tests:** On-time, late, missed EMI scenarios

---

#### 1.12 Stop Rule Engine
**File:** `app/engines/stop_rule_engine.py` (new)

**Functionality:**
- Freeze further tranches if 2+ EMIs are missed
- Flag for officer review
- Return hold reason

**Input:**
```python
{
  "application_id": "app_123",
  "repayment_records": [...]
}
```

**Output:**
```python
{
  "should_freeze": true,
  "missed_emi_count": 2,
  "frozen_date": "2024-12-01",
  "review_required": true,
  "reason": "2 EMIs missed, tranches frozen until review"
}
```

**Tests:** 0, 1, 2+ missed EMIs

---

#### 1.13 Update Scoring Endpoint
**File:** `app/endpoints/scoring.py`

**Modify:** `POST /api/scoring/score`

**Old Logic:**
1. Fetch ABCA
2. Calculate household surplus
3. Run capacity model
4. Apply loan rules
5. Calculate rate
6. Generate EMI schedule
7. Return decision (amount, rate, EMI)

**New Logic:**
1. Fetch AA, GST, UPI data
2. Run Source Agreement Engine
3. Run Verified Window Engine
4. Run Photo Verification Engine
5. Run GST Coverage Engine (if registered)
6. Run Tier Assignment Engine
7. Run Amount Rule Engine
8. Run Rate Calculation Engine
9. Run Tranche Plan Generator
10. Calculate EMI per tranche
11. Save Decision with tier + tranche plan
12. Return decision (tier, amount, tranche_plan, rate, reasons)

**New Input:**
```python
{
  "application_id": "app_123",
  "consent_given": true,
  "family_size": 4,
  "monthly_expenses": 25000  # Expense input only, not EMI cap input
}
```

**New Output:**
```python
{
  "decision_id": "dec_456",
  "tier": 1,
  "approved_amount": 41000,
  "rate_percent": 18.5,
  "tranche_plan": [
    {"tranche_num": 1, "amount": 41000, "release_date": "2024-11-20"}
  ],
  "emi_schedule": [
    {"month": 1, "amount": 3800, "principal": 3400, "interest": 400},
    ...
  ],
  "verified_months": 10,
  "source_agreement": 0.82,
  "location_verified": true,
  "photo_count": 3,
  "reasons": [
    "Verified 10 months of bank data",
    "AA and UPI agree on sales 82%",
    "Shop location verified",
    "Tier 1: Quick loan for emerging businesses"
  ],
  "next_tier_criteria": [
    "Register for GST",
    "6+ months on-time repayment"
  ]
}
```

**Tests:** Full scoring flow

---

#### 1.14 Tranche Endpoints (New)
**File:** `app/endpoints/tranche.py` (new)

**Endpoints:**
- `GET /api/applications/{id}/tranches` - List all tranches
- `GET /api/applications/{id}/tranches/{tranche_num}` - Get tranche details
- `POST /api/applications/{id}/tranches/{tranche_num}/approve` - Officer approves tranche release
- `GET /api/applications/{id}/tranches/{tranche_num}/eligibility` - Check if next tranche eligible

**Tests:** Tranche retrieval, eligibility check, approval workflow

---

#### 1.15 Repayment Endpoints (New)
**File:** `app/endpoints/repayment.py` (new)

**Endpoints:**
- `GET /api/applications/{id}/repayment` - View EMI history
- `POST /api/applications/{id}/repayment/record` - Record EMI payment (admin)
- `GET /api/applications/{id}/repayment/next-emi` - Get next EMI due
- `GET /api/audit/repayment-monitor` - Officer view of all borrowers' EMI status

**Tests:** EMI tracking, payment recording, status views

---

#### 1.16 Photo Endpoints (New)
**File:** `app/endpoints/photos.py` (new)

**Endpoints:**
- `POST /api/applications/{id}/photos` - Upload geo-tagged photo
- `GET /api/applications/{id}/photos` - List photos
- `GET /api/applications/{id}/photos/{photo_id}` - Get photo details + verification status

**Tests:** Photo upload, retrieval, verification status

---

#### 1.17 Phase 1 Tests
**Files:** `tests/test_phase1_*.py`

**Test Coverage:**
- 1.1: Model creation, relationships (20 tests)
- 1.2: Rate adapter (5 tests)
- 1.3: Photo verification (12 tests)
- 1.4: Source agreement (15 tests)
- 1.5: Verified window (10 tests)
- 1.6: GST coverage (8 tests)
- 1.7: Tier assignment (20 tests)
- 1.8: Amount rule (15 tests)
- 1.9: Rate calculation (8 tests)
- 1.10: Tranche plan (12 tests)
- 1.11: Tranche rule (10 tests)
- 1.12: Stop rule (8 tests)
- 1.13-1.16: Endpoint tests (50 tests)

**Total Phase 1 Tests:** ~200 tests
**Target Coverage:** >85%

---

### Phase 1 Deliverables

✅ Complete data model (12 new tables)
✅ 9 business logic engines
✅ Rate environment management
✅ Tier-based workflow
✅ Multi-tranche system
✅ Photo verification
✅ Repayment tracking
✅ Stop rules
✅ 200+ tests (>85% coverage)

**At end of Phase 1:** System can score an application, assign tier, generate tranche plan, verify photos, and track repayment.

---

## Phase 2: Polish & Refinement (Weeks 3-4)

Refine Phase 1 to production quality, add data integrity checks, implement plain-language layer, and prepare for Stage 3.

**Effort:** ~4 days

### Phase 2 Tasks

#### 2.1 Data Validation & Integrity Checks
**Files:** `app/validators/` (new directory)

**Validators:**
- `validate_application()` - Check required fields, consent, documents
- `validate_tier_assignment()` - Verify tier rules are met, no impossible states
- `validate_tranche_plan()` - Verify tranche amounts sum to approved amount
- `validate_repayment()` - Check EMI payments, status transitions

**Tests:** Edge cases, invalid data rejection

---

#### 2.2 Error Handling & Logging
**Files:** `app/utils/error_handler.py` (new)

**Implement:**
- Comprehensive exception hierarchy
- Structured logging (JSON logs with context)
- User-friendly error messages (different for borrower vs officer)
- Error tracking (Sentry integration, optional)

**Errors to handle:**
- Missing AA/GST/UPI data
- Photo verification failure
- Insufficient verified months
- Invalid tier assignment
- Tranche eligibility check failure
- Repayment recording errors

**Tests:** Error scenarios, logging output

---

#### 2.3 Plain Language Layer
**File:** `app/templates/reasons.py` (new)

**Dictionary of reason templates:**
```python
TIER_REASONS = {
  "insufficient_data": "We need at least 6 months of bank data to assess your loan",
  "source_agreement_weak": "Your bank data and shop sales don't align well, so we're being cautious",
  "photo_verified": "We checked your shop location and it matches your rent agreement",
  "no_gst": "You're not registered for GST yet. Getting registered helps with future loans",
}

NEXT_TIER_REASONS = {
  "register_gst": "Register for GST to unlock Tier 2 loans (up to ₹2.5L)",
  "udyam": "Register for Udyam (takes 10 minutes) to unlock Tier 3 (up to ₹10L)",
  "repayment_history": "After 6 months of on-time payments, you can move to Tier 2",
}
```

**Function:** `generate_plain_reasons(decision_data) -> List[str]`

**Tests:** Reason generation for all scenarios

---

#### 2.4 Glossary & Help System
**Files:** `app/templates/glossary.py` (new)

**Terms:**
- Tier 1, 2, 3
- ABCA (now called "Sales verification")
- Tranche
- EMI
- Udyam
- GSTR-2B
- Account Aggregator

**Each term includes:** Simple definition + example + link to more info

**Tests:** Glossary completeness, rendering

---

#### 2.5 Audit Trail Enhancement
**File:** `app/models.py` (extend AuditLog)

**Log every action:**
- Application created, consent given, data uploaded
- Scoring run, tier assigned
- Tranche released, repayment recorded
- Override applied, stop rule triggered

**Fields:** entity_type, entity_id, action, user_id/officer_id, timestamp, old_value, new_value, reason

**Tests:** Audit creation for all operations

---

#### 2.6 Officer Dashboard Views (Backend APIs)
**Files:** `app/endpoints/dashboard.py` (new)

**Endpoints:**
- `GET /api/dashboard/queue` - Pending applications (count by tier)
- `GET /api/dashboard/repayment-status` - All borrowers' EMI status
- `GET /api/dashboard/stats` - Approval rate, average loan amount, tranche release rate by tier
- `GET /api/dashboard/alerts` - Missed EMIs, frozen accounts, upcoming tranches

**Tests:** Dashboard data accuracy

---

#### 2.7 Synthetic Data Update
**File:** `synth/generator.py` (extend)

**Update:**
- Label each shop as Tier 1, 2, or 3
- Generate tier-appropriate data:
  - Tier 1: 6 months AA + UPI, no GST, no Udyam
  - Tier 2: 12+ months AA + UPI + GST
  - Tier 3: 24+ months AA + GST + Udyam + prior repayment
- Generate synthetic **repayment history** (on-time, late, missed, bounced)
- Generate synthetic **tranche release** data (next tranche eligible, etc.)

**Tests:** Tier-appropriate data generation, repayment outcome distribution

---

#### 2.8 Golden Test Cases Update
**File:** `tests/golden_expected_phase2.csv`

**Test 10 borrowers covering:**
- Tier 1 approval
- Tier 1 rejection (< 6 months data)
- Tier 2 approval
- Tier 2 rejection (no GST)
- Tier 3 approval
- Weak source agreement (Tier 1 only)
- Strong source agreement (higher tier eligible)
- Tranche release gates working
- Stop rule triggering on missed EMI

**Tests:** All golden cases pass

---

#### 2.9 Integration Tests: Full Borrower Journey
**File:** `tests/test_integration_phase2_e2e.py`

**Scenarios:**

1. **Tier 1 Borrower:**
   - Apply → Consent → Upload 3 photos → Score → Tier 1 assigned
   - Amount ₹41K single tranche → EMI ₹3.8K × 12 months
   - Pay 3 EMIs on-time → Repayment status
   - Check next-tier criteria (register GST)

2. **Tier 2 Borrower:**
   - Apply → Consent → Upload photos, rent agreement, GSTR-2B → Score → Tier 2 assigned
   - Amount ₹200K in 2 tranches (₹120K now, ₹80K at +60d)
   - Pay tranche 1 EMIs → Tranche 2 eligibility check → Release tranche 2
   - Repayment tracking

3. **Stop Rule Trigger:**
   - Tier 1 borrower misses 1 EMI → Late notice
   - Misses 2 EMIs → Frozen, review required
   - Officer reviews, unfreezes with note

4. **Officer Workflow:**
   - Queue view (10 pending, 3 Tier 1, 5 Tier 2, 2 Tier 3)
   - Case view (see each source, agreements, tier reasons)
   - Replay: change verified_months from 10 to 8 → Tier drops to rejected
   - Override: force Tier 2 (risky) with reason "Personal referral"

**Tests:** All scenarios pass end-to-end

---

#### 2.10 API Documentation Update
**File:** `API_DOCS_PHASE2.md`

**Document:**
- All new endpoints (photo, tranche, repayment, dashboard)
- Request/response schemas
- Tier assignment logic
- Rate calculation
- Tranche gates
- Stop rules

**Tests:** Schema validation

---

#### 2.11 Migration Guide
**File:** `MIGRATION_STAGE2_TO_PHASE2.md`

**Document:**
- Database migration steps (add new tables, populate Tier table)
- Breaking API changes (scoring endpoint output changed)
- Deprecations (capacity_model removed, loan_rules renamed)
- Backward compatibility plan (if any)

---

#### 2.12 Phase 2 Tests
**Files:** `tests/test_phase2_*.py`

**Test Coverage:**
- 2.1: Validation (25 tests)
- 2.2: Error handling (20 tests)
- 2.3: Plain language (15 tests)
- 2.4: Glossary (5 tests)
- 2.5: Audit trail (15 tests)
- 2.6: Dashboard (12 tests)
- 2.7: Synthetic data (10 tests)
- 2.8: Golden cases (10 tests)
- 2.9: E2E scenarios (20 tests)

**Total Phase 2 Tests:** ~130 tests
**Target Coverage:** >85% (maintain from Phase 1)

---

### Phase 2 Deliverables

✅ Data validation layer
✅ Comprehensive error handling
✅ Plain-language reason generation
✅ Glossary & help system
✅ Enhanced audit trail
✅ Officer dashboard APIs
✅ Updated synthetic data
✅ Updated golden test cases
✅ Full e2e integration tests
✅ API documentation
✅ Migration guide
✅ 130+ tests (>85% coverage)
✅ Production-ready codebase

**At end of Phase 2:** Complete, tested, documented tiered verification-first lending system ready for Stage 3 (fairness audit, scenario simulation, export).

---

## Summary: Two-Phase Migration

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| **Duration** | Weeks 1-2 (~5 days) | Weeks 3-4 (~4 days) |
| **Focus** | Core engines & data model | Polish, validation, docs |
| **New Tables** | 9 | 0 (models complete) |
| **New Engines** | 9 | 0 (engines complete) |
| **New Endpoints** | 6 | 1 (dashboard) |
| **Tests** | ~200 | ~130 |
| **Coverage** | >85% | >85% |
| **Deliverable** | Functional tiered system | Production-ready product |

---

## Key Changes from Stage 2 to Phase 2

### Data
- ✅ Tier table replaces risk bands
- ✅ Tranche table for multi-tranche loans
- ✅ Photo, SourceAgreement, VerifiedWindow, GSTCoverage tables
- ✅ RepaymentRecord, StopRule for enforcement

### Logic
- ✅ Tier-based scoring (not risk band)
- ✅ Multi-tranche with repayment gates (not single lump-sum)
- ✅ Industry rate + adjustment (not fixed rate per band)
- ✅ Verified window (not capacity model)
- ✅ Photo verification (new)
- ✅ Source agreement check (replaces ABCA)

### Workflows
- ✅ Borrower journey: Apply → Tier → Tranche plan → Track repayment
- ✅ Officer workflow: Queue → Case view → Replay → Override → Audit
- ✅ Stop rule: Freeze tranches on 2 missed EMIs

### Quality
- ✅ Full error handling
- ✅ Plain language for borrowers
- ✅ Comprehensive audit trail
- ✅ Data validation at every step
- ✅ Officer dashboard
- ✅ 330+ tests, >85% coverage

---

## Ready to Begin?

Phase 1 and 2 together will transform the current generic credit system into the tiered, verification-first product you've outlined.

**Next Steps:**
1. Approve Phase 1 & 2 plan
2. Launch Phase 1 implementation workflow
3. Verify Phase 1 deliverables
4. Launch Phase 2 workflow

Want me to start Phase 1 implementation?
