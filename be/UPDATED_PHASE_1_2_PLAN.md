# Updated Phase 1 & 2 Implementation Plan
## Current Status & Next Steps (Nov 2026)

---

## What's Already Complete ✅

### Phase 1 Foundation (COMPLETE)
- **10 new database models** with relationships and cascade deletes (Tier, Photo, SourceAgreement, VerifiedWindow, GSTCoverage, Tranche, RepaymentRecord, StopRule, LocationVerification, RateEnvironment)
- **9 business logic engines** fully implemented:
  1. Photo Verification Engine (geo-tag + code detection)
  2. Source Agreement Engine (AA 60% + GST 30% + UPI 10%)
  3. Verified Window Engine (6+ months minimum)
  4. GST Coverage Engine (purchases vs GST reconciliation)
  5. Tier Assignment Engine (Tier 1/2/3 rules)
  6. Amount Rule Engine (scaled by verification + agreement)
  7. Rate Calculation Engine (industry rate + tier adjustment)
  8. Tranche Plan Generator (1/2/4 tranches by tier)
  9. Tranche Rule Engine (next tranche eligibility)
  10. Stop Rule Engine (freeze on 2+ missed EMIs)
- **Rate Adapter** (fetches industry rates from RateEnvironment table)
- **4 new endpoint files** (photos, tranches, repayment, scoring_phase1)
- **33 Phase 1 tests passing** (11 models, 22 engines)

### Stage 2 (Existing, Already Wired)
- **8 business logic engines** (ABCA, vintage, round-trip, EMI, capacity, loan rules, rate, fund split)
- **8 API endpoint groups** (19 total endpoints) - scoring, applications, consent, documents, household, audit, override, replay
- **286 tests passing** (76% coverage)
- Full Stage 1 maintained (GSTIN validator, reconciliation, tests)

### Current Test Suite
- **548 total tests passing** (286 Stage 2 + 33 Phase 1 + 229 Stage 1)
- **70% overall coverage**
- **85%+ coverage on critical engines**

---

## What Needs to Happen: Phase 2 (Weeks 3-4)

### Phase 2 Overview
Complete the tiered verification-first system with plain language, validation, error handling, and production readiness.

### Phase 2 Task Breakdown

#### **Task 2.1: Data Validation Layer** (1 day)
**Objective:** Comprehensive input validation across all flows

**Files to create:**
- `app/validators/__init__.py`
- `app/validators/application_validator.py`
- `app/validators/tier_validator.py`
- `app/validators/tranche_validator.py`
- `app/validators/repayment_validator.py`

**Validators to implement:**
1. `validate_application()` - Required fields, consent, documents
2. `validate_tier_assignment()` - Tier rules met, no impossible states
3. `validate_tranche_plan()` - Amounts sum correctly, release dates logical
4. `validate_repayment()` - EMI amounts, status transitions valid
5. `validate_photo()` - File format, code presence, location data
6. `validate_gst_coverage()` - Coverage % within 0.8-1.2 range

**Tests:** 25 tests covering edge cases, invalid data

---

#### **Task 2.2: Error Handling & Structured Logging** (1 day)
**Objective:** Comprehensive exception handling and audit logging

**Files to create:**
- `app/utils/error_handler.py`
- `app/utils/audit_logger.py`
- `app/exceptions.py`

**Implement:**
1. **Custom Exceptions:**
   - `InvalidTierError`
   - `InsufficientVerificationError`
   - `PhotoVerificationFailedError`
   - `FrozenApplicationError`
   - `IncompleteApplicationError`

2. **Error Responses (all endpoints):**
   - 400 Bad Request (validation errors)
   - 403 Forbidden (permission/frozen status)
   - 404 Not Found (resource missing)
   - 409 Conflict (duplicate/state conflict)
   - 422 Unprocessable (Pydantic validation)
   - 500 Internal Error (database/adapter failures)

3. **Structured Logging:**
   - JSON format logs with context
   - Log levels: DEBUG, INFO, WARNING, ERROR
   - Track: user_id, application_id, action, timestamp, result

4. **Audit Trail:**
   - Log all scoring runs (inputs, engines, outputs)
   - Log all overrides (who, why, old vs new)
   - Log all tranches (eligibility checks, releases)
   - Log all repayments (EMI, status, freeze triggers)

**Tests:** 20 tests for error scenarios, logging output

---

#### **Task 2.3: Plain Language Layer** (1 day)
**Objective:** Convert technical outputs to borrower-friendly text

**File to create:**
- `app/templates/reasons.py`

**Dictionaries to implement:**
```python
TIER_REASONS = {
    "verified_months": "Verified {months} months of bank data (required {min}+)",
    "source_agreement": "Your bank and shop sales agree {percent}% (good match)",
    "location_verified": "Shop location verified with rent agreement",
    "no_gst": "You're not registered for GST yet",
    "low_agreement": "Bank and shop data don't align well",
}

NEXT_TIER_REASONS = {
    "register_gst": "Register for GST (free, 10 mins) to unlock Tier 2 (₹250K)",
    "udyam_cert": "Get Udyam certificate (free, online) to unlock Tier 3 (₹1M)",
    "repayment_history": "After 6 months of on-time payments, you can move up",
    "more_data": "We need 12 months of bank data for the next tier",
}

SOURCE_REASONS = {
    "aa_only": "Only your bank account data is available",
    "gst_available": "Your GST filing shows consistent sales",
    "upi_supplementary": "Your UPI payments confirm the trend",
}

VERIFICATION_REASONS = {
    "6_months": "You have 6+ months of verified bank data",
    "12_months": "You have 12+ months of verified records",
    "24_months": "You have 24+ months of business history",
}

TIER_NAMES = {
    1: "Quick Loan (Tier 1): Fast approval, up to ₹50,000, 12-month tenure",
    2: "Standard Loan (Tier 2): Larger amount, up to ₹2,50,000, 24-month tenure",
    3: "Business Loan (Tier 3): Maximum support, up to ₹10,00,000, 36-month tenure",
    0: "Insufficient Data: We need more information to assess your loan"
}
```

**Functions to implement:**
1. `generate_tier_explanation(tier: int) -> str`
   - Human-readable tier name and limits

2. `generate_decision_reasons(decision: Decision) -> List[str]`
   - Convert decision factors to borrower-friendly bullets
   - Example output:
     ```
     • Verified 10 months of bank data
     • Your bank account and shop sales match 82%
     • Shop location confirmed with rent agreement
     • Tier 1 approved: Quick loan up to ₹50,000
     ```

3. `generate_next_tier_steps(decision: Decision) -> List[str]`
   - Actionable steps to qualify for next tier
   - Example output:
     ```
     • Register for GST (takes 10 minutes online)
     • Make your EMI payments on time
     • After 6 months, reapply for Tier 2 (₹250K limit)
     ```

4. `generate_source_summary(decision: Decision) -> str`
   - Explain which data sources were checked

**Integration:**
- Wire into `scoring_phase1.py` endpoint
- Include `reasons` and `next_steps` in Decision response
- Also include `plain_language_tier_name`

**Tests:** 15 tests verifying reason generation for all tiers and scenarios

---

#### **Task 2.4: Glossary & Help System** (0.5 day)
**Objective:** Define financial terms for borrowers

**File to create:**
- `app/templates/glossary.py`

**Terms to define (12+):**
```python
GLOSSARY = {
    "tier": {
        "simple": "Groups of loans based on your business records",
        "detail": "Tier 1 is fastest (up to ₹50K), Tier 2 is bigger (₹250K), Tier 3 is biggest (₹1M)",
        "example": "If you have 6 months of bank records, you qualify for Tier 1"
    },
    "emi": {
        "simple": "Monthly payment you make to repay the loan",
        "detail": "Fixed amount each month, includes principal and interest",
        "example": "₹4,000 per month for 12 months = ₹48,000 total paid for ₹40,000 loan"
    },
    "gst": {
        "simple": "Goods and Services Tax registration",
        "detail": "Proof you report your business sales to government",
        "example": "Required to unlock Tier 2 and Tier 3 loans"
    },
    "udyam": {
        "simple": "Free business registration certificate",
        "detail": "Shows government you're a registered MSME",
        "example": "Needed for Tier 3 loans, free to register online"
    },
    "tranche": {
        "simple": "Part of your total loan released over time",
        "detail": "You get some money now, rest later if repayment is on-time",
        "example": "Tier 2: ₹60K now, ₹40K after 2 months of on-time payments"
    },
    "account_aggregator": {
        "simple": "Service that fetches your real bank account data",
        "detail": "Secure way to share bank records without giving passwords",
        "example": "Shows us your actual deposits, not just your word"
    },
    "stock_verification": {
        "simple": "Check if shop goods match sales",
        "detail": "We verify your purchase records match what you're selling",
        "example": "If you buy ₹100K stock, you should sell about ₹108-110K"
    },
    "repayment_history": {
        "simple": "Record of how you've paid previous loans",
        "detail": "Helps us see if you pay on-time",
        "example": "Tier 3 requires at least one previous loan paid on-time"
    },
}
```

**Function:**
- `get_glossary_term(term: str) -> Dict[str, str]`
  - Returns simple, detail, example

**Tests:** 5 tests verifying glossary completeness and retrieval

---

#### **Task 2.5: Audit Trail Enhancement** (0.5 day)
**Objective:** Comprehensive audit logging for all operations

**Enhance:**
- `AuditLog` model (add fields if needed)
- All scoring runs (what inputs, which engines, what output)
- All tier assignments (why Tier 1 vs 2 vs 3)
- All tranche releases (eligibility check result, who approved)
- All repayments (which EMI, on-time or late, stop rule triggered)
- All overrides (old decision, new decision, officer reason)
- All freezes (missed EMI count, who unfroze)

**Log fields:**
- entity_type: application|decision|tranche|repayment|override|freeze
- entity_id: application_id or decision_id etc.
- action: created|updated|scored|released|recorded|frozen|overridden
- user_id: who did it (officer/system)
- timestamp: when
- old_value: what changed from
- new_value: what changed to
- reason: why (officer override reason, stop rule reason, etc.)
- context: JSON with additional details

**Tests:** 15 tests verifying audit logging for all operations

---

#### **Task 2.6: Officer Dashboard APIs** (1 day)
**Objective:** Views for officers to manage applications and repayments

**File to create:**
- `app/endpoints/dashboard.py`

**Endpoints to implement:**

1. **GET /api/dashboard/queue**
   - List pending applications (not yet scored or decision pending)
   - Filter by tier (optional)
   - Sort by application date
   - Return: count by tier, application list with summaries

2. **GET /api/dashboard/repayment-status**
   - All borrowers' current EMI status
   - Group by: on-time, late, missed, bounced
   - Show: next EMI due date, tranche frozen status
   - Return: borrower list with EMI summary

3. **GET /api/dashboard/stats**
   - Approval rate: (approved / total) * 100
   - Average loan amount by tier
   - Tranche release success rate (how many second tranches released)
   - Average repayment performance (% on-time)
   - Approval breakdown by tier (e.g., 50% Tier 1, 40% Tier 2, 10% Tier 3)

4. **GET /api/dashboard/alerts**
   - Applications needing officer attention:
     - Missed EMIs (count > 0)
     - Frozen applications (count > 0)
     - Tranches pending approval (count)
     - High-value applications (> ₹500K) requiring review

**Tests:** 12 tests for dashboard accuracy, filters, aggregations

---

#### **Task 2.7: Synthetic Data Generation Update** (0.5 day)
**Objective:** Generate test data labeled by tier with repayment outcomes

**Enhance `synth/generator.py`:**

1. **Label shops by tier** (Tier 1, 2, 3)
   - Tier 1: 6 months AA + UPI, no GST, no Udyam
   - Tier 2: 12+ months AA + UPI + GST registered, no Udyam
   - Tier 3: 24+ months AA + GST + Udyam registered

2. **Generate synthetic repayment history**
   - On-time: 60% of Tier 1, 80% of Tier 2, 90% of Tier 3
   - Late (1-15 days): 30% of Tier 1, 15% of Tier 2, 8% of Tier 3
   - Missed (>15 days): 10% of Tier 1, 5% of Tier 2, 2% of Tier 3
   - Bounced: 5% of Tier 1, 2% of Tier 2, 0% of Tier 3

3. **Generate tranche release data**
   - Tier 1: 1 tranche, always released
   - Tier 2: 2 tranches, 90% get tranche 2, 10% frozen before tranche 2
   - Tier 3: 4 tranches, 85% get tranche 2+, 10% frozen at tranche 2, 5% frozen at tranche 3

**Tests:** 10 tests verifying tier-appropriate data, repayment distributions

---

#### **Task 2.8: Golden Test Cases Update** (0.5 day)
**Objective:** Pre-computed test verdicts covering all scenarios

**Create `tests/golden_expected_phase2.csv`:**

10 shops with scenarios:
1. **Shop 0: Tier 1 Approval** - 6mo AA+UPI, agreement 85%, photos verified
2. **Shop 1: Tier 1 Rejection** - 4mo AA only, insufficient data
3. **Shop 2: Tier 2 Approval** - 12mo AA+GST, agreement 80%, GST coverage 95%
4. **Shop 3: Tier 2 Rejection** - 12mo AA but no GST, not eligible for Tier 2
5. **Shop 4: Tier 3 Approval** - 24mo AA+GST+Udyam, prior repayment on-time
6. **Shop 5: Weak Agreement** - 6mo AA but agreement only 65%, drops to Tier 1
7. **Shop 6: Strong Agreement** - 10mo AA+GST, agreement 90%, higher amount eligible
8. **Shop 7: Tranche Gates** - Tier 2, tranche 1 on-time, tranche 2 eligible
9. **Shop 8: Stop Rule** - Tier 1, 2 EMIs missed, application frozen
10. **Shop 9: Pair Case** - Same UPI as Shop 0 but GST mismatch, different verdict

**CSV columns:**
- shop_id, tier_expected, amount_expected, rate_expected, tranche_count_expected, reason

**Tests:** 10 tests comparing golden verdicts to engine outputs

---

#### **Task 2.9: End-to-End Integration Tests** (1 day)
**Objective:** Full workflows for borrowers and officers

**File to create:**
- `tests/test_integration_phase2_e2e.py`

**Test Scenarios:**

1. **Tier 1 Full Borrower Journey** (1 test)
   - Create app → Consent → Upload photos → Record household → Score → Get Tier 1
   - Result: Single tranche ₹41K, 18.5% rate, 12-month EMI
   - Verify: Plain language reasons shown

2. **Tier 2 Full Borrower Journey with Tranches** (1 test)
   - Create app → Consent → Upload photos + GST → Household → Score → Get Tier 2
   - Tranches: ₹120K now, ₹80K at +60d
   - Pay 3 EMIs on-time
   - Result: Tranche 2 eligible, released
   - Verify: Stop rule doesn't trigger

3. **Stop Rule Triggered** (1 test)
   - Tier 1 borrower misses 1 EMI → Late notice
   - Misses 2 EMIs → Frozen
   - Result: Application status = "frozen", tranches blocked
   - Verify: Audit log entry created

4. **Officer Workflow: Review & Approve** (1 test)
   - Queue view shows pending applications
   - Officer reviews Tier 1 app
   - Case view shows all data sources (AA, UPI, photos, GST)
   - Officer approves
   - Result: Decision saved, tranche 1 released

5. **Officer Workflow: Replay & Override** (1 test)
   - Officer loads Tier 1 decision
   - Replays with different household_expenses (lower)
   - Result: Amount goes up, but doesn't save
   - Officer overrides with reason "Manual assessment confirms higher capacity"
   - Result: Override recorded, new decision saved

6. **Tier Progression** (1 test)
   - Tier 1 borrower repays 6+ months on-time
   - Registers for GST
   - Reapply
   - Result: Now qualifies for Tier 2, higher amount

7. **Error Scenarios** (1 test)
   - No consent: scoring blocked, error returned
   - Frozen app: tranche approval blocked
   - Invalid tier: engine rejects with error
   - Bad photo: code verification fails

8. **Dashboard Views** (1 test)
   - Queue shows 3 pending, 2 Tier 1, 1 Tier 2
   - Repayment status shows 10 on-time, 2 late, 1 missed
   - Stats shows 80% approval rate, avg ₹100K amount

**Tests:** 20 tests covering all workflows

---

#### **Task 2.10: API Documentation** (0.5 day)
**Objective:** Complete API reference

**Create `API_DOCS_PHASE2.md`:**

Sections:
1. Overview of Phase 1 & 2 architecture
2. Authentication & authorization (roles)
3. Tier assignment logic (rules, examples)
4. Rate calculation (industry rate + adjustment)
5. Tranche gates (EMI requirements)
6. Stop rules (freeze conditions)
7. Plain language (reason templates)
8. All endpoint schemas (request/response)
9. Error codes and meanings
10. Example workflows (borrower and officer)

---

#### **Task 2.11: Migration Guide** (0.5 day)
**Objective:** Upgrade from Stage 2 to Phase 2

**Create `MIGRATION_STAGE2_TO_PHASE2.md`:**

Sections:
1. **Database migration steps**
   - Add Phase 1 tables (Tier, Photo, etc.)
   - Add Phase 1 fields to Decision model
   - Populate RateEnvironment table

2. **Breaking API changes**
   - POST /api/scoring/score now returns tier instead of loan_amount
   - New fields: tranche_plan, verified_months, source_agreement_score

3. **Deprecations**
   - Capacity model no longer used
   - Fund split engine deprecated
   - Old Decision schema fields nullable

4. **Backward compatibility**
   - Old Decision fields still present (read-only)
   - Old tests will pass but new fields null
   - Gradual migration path for frontend

---

#### **Task 2.12: Phase 2 Test Suite** (1 day)
**Objective:** 130+ new tests for Phase 2 features

**Test files:**
- `tests/test_phase2_validators.py` (25 tests)
- `tests/test_phase2_error_handling.py` (20 tests)
- `tests/test_phase2_reasons.py` (15 tests)
- `tests/test_phase2_glossary.py` (5 tests)
- `tests/test_phase2_audit.py` (15 tests)
- `tests/test_phase2_dashboard.py` (12 tests)
- `tests/test_phase2_synthetic_data.py` (10 tests)
- `tests/test_phase2_golden.py` (10 tests)
- `tests/test_phase2_e2e.py` (20 tests)

**Target:** 130+ tests, >85% coverage

---

## Phase 2 Timeline & Effort

| Task | Days | Status |
|------|------|--------|
| 2.1 Validation | 1 | ⏳ TO DO |
| 2.2 Error Handling | 1 | ⏳ TO DO |
| 2.3 Plain Language | 1 | ⏳ TO DO |
| 2.4 Glossary | 0.5 | ⏳ TO DO |
| 2.5 Audit Trail | 0.5 | ⏳ TO DO |
| 2.6 Dashboard | 1 | ⏳ TO DO |
| 2.7 Synthetic Data | 0.5 | ⏳ TO DO |
| 2.8 Golden Cases | 0.5 | ⏳ TO DO |
| 2.9 E2E Tests | 1 | ⏳ TO DO |
| 2.10 API Docs | 0.5 | ⏳ TO DO |
| 2.11 Migration Guide | 0.5 | ⏳ TO DO |
| 2.12 Test Suite | 1 | ⏳ TO DO |
| **Total** | **~9 days** | **⏳ TO DO** |

---

## Success Criteria for Phase 2

✅ All 130+ tests passing
✅ >85% coverage on Phase 2 code
✅ Plain language working for all tiers
✅ Officer dashboard fully functional
✅ Error handling comprehensive (all HTTP codes covered)
✅ Audit trail logging all operations
✅ Validation catching all invalid states
✅ Documentation complete
✅ All workflows E2E tested
✅ System production-ready

---

## Summary

| Aspect | Phase 1 (DONE) | Phase 2 (TO DO) | Total |
|--------|---|---|---|
| **Tables** | 10 | 0 | 10 |
| **Engines** | 9 | 0 | 9 |
| **Endpoints** | 4 (+ 19 Stage 2) | 1 (dashboard) | 5 new |
| **Tests** | 33 | 130+ | 163+ |
| **Coverage** | 85%+ (engines) | >85% (all) | >85% |
| **Effort** | ~5 days (done) | ~9 days | ~14 days |

---

## Ready to Proceed?

Phase 1 is complete and working. Phase 2 adds the polish, plain language, validation, and documentation.

**Next action:** Start Phase 2 Task 2.1 (Validation Layer) immediately after team sync.
