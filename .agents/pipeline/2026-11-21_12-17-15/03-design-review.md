# Design Review: Phase 1 & 2 Integration Testing & Production Deployment

**Design Document:** 02-design.md  
**Requirements Document:** 01-requirements.md  
**Review Date:** 2024-11-21  
**Reviewer:** Kiro Design Review Agent  
**Verdict:** CHANGES_REQUESTED (5 HIGH, 2 MEDIUM findings)

---

## Findings Summary

**HIGH (5):** Must fix before implementation  
**MEDIUM (2):** Should fix; blocks implementation  
**NIT (2):** Informational

---

## Detailed Findings

### HIGH.1: Missing Tier-Driven Verified Months Logic in Tier Assignment Engine
**Severity:** HIGH  
**Location:** Design Section 1 (Backend Integration & Wiring), Engine Orchestration table; Requirements FR1.3  
**Problem:** The design states "Tier 1 requires 6+ verified months (AA+UPI with no GST)" but doesn't clarify the decision rule. If a borrower has 6+ verified months but the GST requirement is violated (e.g., GST present but not registered), should tier assignment:
- Downgrade to Tier 0 (reject)?
- Downgrade to a lower tier (but there's no Tier 0.5)?
- Allow GST presence but check registration status separately?

**Evidence:** The TierAssignmentEngine code (verified in codebase) exists but the design doesn't specify the exact decision logic for:
- Tier 1: "AA+UPI, no GST (or GST not registered)" — ambiguous phrasing (do both conditions apply, or either?)
- Tier 2: "AA+(GST or UPI), GST registered, no Udyam" — unclear if all three conditions must pass or some are optional
- Interaction with verified_months boundary: Exactly 6.0 months moves to Tier 1, but what if AA has 6+ months but UPI only has 3?

**Fix:** Clarify the exact tier assignment logic with AND/OR:
```
Tier 1: verified_months >= 6 AND (AA_present OR UPI_present) AND NOT GST_registered
Tier 2: verified_months >= 12 AND (AA_present AND (GST_registered OR UPI_present)) AND NOT Udyam_registered
Tier 3: verified_months >= 24 AND AA_present AND GST_registered AND Udyam_registered
Where verified_months = min(aa_months, gst_months, upi_months) if multiple sources present, else single source months
```

Additionally, specify what happens to rejected Tier 0 borrowers — can they reapply? Is there a waiting period?

---

### HIGH.2: PhotoVerificationEngine Not Invoked in Scoring Pipeline
**Severity:** HIGH  
**Location:** Design Section 1, Engine Orchestration step 3; Requirements FR1.6  
**Problem:** The design describes PhotoVerificationEngine as step 3 in the scoring pipeline, but code review shows:
- `photos.py` endpoint saves photos but does NOT call PhotoVerificationEngine for verification
- `scoring_phase1.py` checks `photo.verification_status == "verified"` but never sets this to "verified" — it remains "pending"
- PhotoVerificationEngine exists and has code to verify geolocation (distance calculation, code matching), but is never invoked anywhere

**Evidence:** In `scoring_phase1.py` lines ~220-230:
```python
for photo in photos:
    if photo.verification_status == "verified":
        photo_verified = True
        break
```
This checks if photos were already verified but never calls the engine to perform verification. Photos endpoint just stores them with `verification_status="pending"`.

**Fix:** Add a new endpoint or integrate photo verification into the scoring pipeline:
- **Option A (Recommended):** Add `POST /api/applications/{id}/verify-photos` endpoint that calls PhotoVerificationEngine for each photo and updates `Photo.verification_status` and `Photo.verified_at`
- **Option B:** Auto-verify photos during scoring if EXIF + code data present

Include logic:
```python
from app.engines.photo_verification_engine import PhotoVerificationEngine

for photo in photos:
    result = PhotoVerificationEngine.verify_photo(
        photo_data={
            "location_lat": photo.location_lat,
            "location_lng": photo.location_lng,
            "detected_code": photo.random_code_written,
        },
        expected_code=app.challenge_code,  # Store in Application or Challenge table
        rent_lat=app.shop.rent_lat,  # Need to add rent address to Shop model
        rent_lng=app.shop.rent_lng,
        tolerance_meters=500,
    )
    photo.verification_status = "verified" if (result.code_verified and result.location_verified) else "rejected"
    photo.verified_at = utcnow_naive()
```

---

### HIGH.3: RateCalculationEngine RateAdapter Not Wired; Hardcoded Rates Used
**Severity:** HIGH  
**Location:** Design Section 1, Engine Orchestration step 9; code `scoring_phase1.py`  
**Problem:** The design claims "Fetch industry rate from RateAdapter by tier" and shows a RateCalculationEngine, but:
- RateCalculationEngine passes `db` parameter but `rate_adapter.py` likely just returns fixed rates per tier
- No actual external rate lookup happens (matches out-of-scope O5: "Real Rate Environment Data")
- Design doesn't clarify whether rates are stored in a `RateEnvironment` table or hardcoded

**Evidence:** Requirements state "Rates hardcoded per tier in `RateEnvironment` table or policy config" (O5), but design section 1 says "Fetch industry rate from RateAdapter by tier" without clarifying which approach is used.

**Fix:** Clarify and document:
1. Is `RateEnvironment` table used? If so, add schema to models.py if missing
2. Define RateAdapter contract in design:
```
RateAdapter.get_rate(tier: int, db: Session) -> dict:
  Returns: {"base_rate": 20.0, "adjustment": -3.0, "final_rate": 17.0}
  - Tier 1: 20% base, +5% adjustment = 25%
  - Tier 2: 20% base, +0% adjustment = 20%
  - Tier 3: 20% base, -3% adjustment = 17%
```
3. Verify RateCalculationEngine actually calls RateAdapter and doesn't hardcode

Also update design's error handling table to include "Rate lookup fails" scenario.

---

### HIGH.4: Missing Challenge Code / Random Code Generation and Storage
**Severity:** HIGH  
**Location:** Requirements FR1.6 (Challenge code verification), Design Section 1 (PhotoVerificationEngine)  
**Problem:** The design requires "challenge code verification (text/QR code detection)" but:
- Where is the random code generated and stored?
- Design mentions `expected_code` in PhotoVerificationEngine but doesn't specify where it comes from
- `Application` or `Photo` model should store this, but it's unclear
- No endpoint or workflow documented to generate challenge codes for borrowers

**Evidence:** PhotoVerificationEngine calls `verify_code_presence(expected_code, detected_code)` but design doesn't specify:
- Who generates `expected_code`?
- Is it per-application or per-photo?
- Timing: before or after photo upload?
- Display: how does borrower know what code to write?

**Fix:** Add to design:
1. New table or column: `Application.challenge_code` or `Challenge` table with `code`, `created_at`, `expires_at`
2. New endpoint: `POST /api/applications/{id}/generate-challenge` → returns `{"code": "ABC123XYZ", "expires_in_minutes": 30}`
3. Update PhotoVerificationEngine contract to show code generation:
```python
# Step 1: Generate challenge
challenge = ChallengeService.generate_code(application_id)
# Frontend displays challenge.code to borrower
# Borrower writes code in photo
# Step 2: Verify challenge (in PhotoVerificationEngine)
PhotoVerificationEngine.verify_photo(..., expected_code=challenge.code)
```

---

### HIGH.5: Glossary Endpoint Not Defined; Plain Language Reasons Data Structure Unclear
**Severity:** HIGH  
**Location:** Design Section 2 (Frontend Integration), Plain Language Glossary table; Requirements FR1.7, AC1.7  
**Problem:** The design lists 18 glossary terms but:
- No `GET /api/glossary` endpoint documented in endpoint wiring table
- No schema defined for glossary response (just a table of terms)
- No mechanism to ensure 18 terms are synced between frontend glossary and backend reason templates
- `generate_plain_reasons()` function called in scoring_phase1.py but not defined in design

**Evidence:** Design Section 1 table "Endpoint Wiring Checklist" has no glossary endpoint. Section 2 shows a glossary table but no API schema. Test 7 (Plain Language Reasons) expects glossary endpoint to exist but it's not in the design spec.

**Fix:** Add to design:
1. New endpoint in wiring table:
```
| GET /api/glossary | Fetch glossary terms | None | Working | Already implemented? |
```
2. Define response schema:
```json
{
  "terms": {
    "Account Aggregator": {
      "plain_text": "Bank account data verified for 6+ months",
      "category": "Data Verification",
      "examples": ["We confirmed 12 months of your bank transactions"]
    },
    ...
  },
  "version": "1.0"
}
```
3. Document mapping between reason templates and glossary terms:
```python
# In templates/reasons.py
GLOSSARY_MAPPINGS = {
    "tier_1": "Tier 1",
    "verified_months_6": "Verified Window",
    ...
}
```
4. Add test requirement: Verify all 18 terms defined in glossary match reason template references

---

### MEDIUM.1: TrancheRuleEngine Eligibility Check Missing Explicit Preconditions
**Severity:** MEDIUM  
**Location:** Design Section 1, Engine Orchestration step ~13 (TrancheRuleEngine invocation); Requirements FR1.4  
**Problem:** The design describes TrancheRuleEngine as checking "prior EMI history before releasing" but doesn't define:
- What constitutes "prior EMI history"? All prior tranches, or just immediately prior tranche?
- Definition of "on-time": ≤ due date, or ≤ due date + grace period?
- Grace period: Does a 1-day late payment fail the check or pass?
- What if prior tranche has 0 EMIs (released but not yet due)? Can next tranche release?

**Evidence:** Tranche.release_status and RepaymentRecord.payment_status exist, but the exact eligibility rule isn't formally specified in the design.

**Fix:** Clarify TrancheRuleEngine logic in design:
```
Eligibility Check Before Release:
1. Get previous tranche (tranche_num - 1)
2. If no previous tranche: ELIGIBLE (first tranche always releases on approval)
3. If previous tranche exists:
   - Get all RepaymentRecords for previous tranche
   - If previous tranche EMI count > 0:
     - Check ALL EMIs: payment_status must be "ontime" (paid_date <= due_date)
     - If ANY EMI has payment_status != "ontime": NOT ELIGIBLE
     - If ALL EMIs have payment_status == "ontime": ELIGIBLE
   - If previous tranche EMI count == 0 (not yet due): 
     - NOT ELIGIBLE (must wait for first EMI to be paid on-time first)
4. Return ELIGIBLE or NOT_ELIGIBLE with reason
```

---

### MEDIUM.2: Load Test Configuration Incomplete; Missing Baseline Metrics
**Severity:** MEDIUM  
**Location:** Design Section 5 (Load Testing), Tests 1-4  
**Problem:** The design includes load test config but lacks:
- Baseline metrics (1 concurrent user) to compare peak against
- Database size specification: "10,000 applications" mentioned but unclear if this includes all related data (tranches, EMIs, photos, documents, etc.)
- Memory allocation assumption: "2GB available" but no justification or measurement instruction
- Pre-load warmup: Do connections, caches warm up before measuring, or measure cold start?

**Evidence:** Test 3 mentions "10,000 applications in database (simulated historical load)" but doesn't specify how to generate this data or how many related records per application.

**Fix:** Add to load test section:
1. **Baseline (1 concurrent user, cold start):**
   - Expected response time: <500ms (p95)
   - Expected memory: <300MB
   - Record these as baseline for peak comparison
2. **Database Generation Script:**
   ```
   10,000 applications with:
   - 2 tranches per app (average)
   - 24 EMIs per tranche (24-month tenor)
   - 3 photos per app
   - 5 documents per app
   = ~720,000 total records (estimate disk footprint: 100-200MB for SQLite)
   ```
3. **Warmup Phase:** Run 30 seconds of load before measuring (allow connection pool fill, cache priming)
4. **Memory Baseline:** Document machine spec (2GB RAM on what OS? What other processes?)

---

### NIT.1: End-to-End Data Flow Diagram Incomplete
**Severity:** NIT  
**Location:** Design Section 7 (Integration Points & Data Flow)  
**Problem:** Data flow shows Borrower → Backend → Officer → ML but doesn't show error/retry paths, timeout handling, or failure states.

**Fix (Optional):** Add error flow: "If scoring fails due to timeout, return 500 + reason to frontend; frontend displays 'Try again later'; borrower can resubmit."

---

### NIT.2: Glossary Terms Category Mismatch
**Severity:** NIT  
**Location:** Design Section 2, Plain Language Glossary table  
**Problem:** Glossary lists 18 terms in 6 categories, but frontend checklist in requirements (if referenced elsewhere) might define different categories or term counts.

**Fix (Optional):** Cross-check glossary with frontend checklist to ensure alignment. If frontend has 20 terms and backend has 18, specify how to merge.

---

## Verified Assumptions

✅ **A1: 9 Phase 1 Engines Implemented**
- Verified in codebase: All 9 engines exist and have business logic
  - photo_verification_engine.py
  - source_agreement_engine.py
  - verified_window_engine.py
  - gst_coverage_engine.py
  - tier_assignment_engine.py
  - amount_rule_engine.py
  - rate_calculation_engine.py
  - tranche_plan_engine.py
  - tranche_rule_engine.py
  - stop_rule_engine.py

✅ **A2: StopRuleEngine Invoked on Repayment**
- Verified in `repayment.py` lines ~73-125: `StopRuleEngine.check_and_apply()` called after recording EMI, freeze triggered if needed

✅ **A3: Database Schema Finalized**
- Verified in `models.py`: Decision model has correct fields (tier, verified_months, source_agreement_score, approved_amount, rate_percent, tranche_plan_json, reasons_json)

✅ **A4: Scoring Endpoint Wired**
- Verified in `scoring_phase1.py`: POST /api/scoring/score orchestrates engines 1-10 in sequence

✅ **A5: Deterministic Adapters**
- Verified: All adapters (aa, gst, upi) return mock data from DataSource table, no randomness

---

## Unverified / Wrong Assumptions

❌ **U1: PhotoVerificationEngine Invoked During Scoring**
- **Assumption:** "Step 3: PhotoVerificationEngine verifies photo format, EXIF, geolocation, challenge code"
- **Finding:** NOT INVOKED. Scoring pipeline checks `photo.verification_status == "verified"` but never calls engine to verify.
- **Status:** WRONG — See HIGH.2

❌ **U2: RateAdapter Fetches Industry Rates**
- **Assumption:** "Fetch industry rate from RateAdapter by tier"
- **Finding:** RateAdapter likely returns hardcoded rates per tier (matches out-of-scope O5), but design doesn't clarify
- **Status:** UNVERIFIED — See HIGH.3

❌ **U3: Challenge Code Generation Implemented**
- **Assumption:** "Challenge code verification (text/QR code detection)"
- **Finding:** No challenge code generation, storage, or display mechanism documented
- **Status:** WRONG — See HIGH.4

❌ **U4: Glossary Endpoint Implemented**
- **Assumption:** "Verify Glossary endpoint returns all 18 terms with definitions"
- **Finding:** No endpoint defined in design or endpoint wiring table
- **Status:** UNVERIFIED — See HIGH.5

❌ **U5: TrancheRuleEngine Eligibility Logic Fully Specified**
- **Assumption:** "Prior EMI history checked before releasing tranche"
- **Finding:** Exact eligibility criteria not formally defined (all prior tranches vs. immediately prior? Grace period for lateness?)
- **Status:** UNVERIFIED — See MEDIUM.1

---

## Impact Assessment

**If Unfixed, High Findings Will Cause:**
1. **HIGH.1:** Tier assignment logic ambiguous → Engineering guess at implementation → Potential mismatch with requirements
2. **HIGH.2:** Photos uploaded but never verified → Photo verification test (Test 6) fails → Integration test suite incomplete
3. **HIGH.3:** Rates unclear (hardcoded vs. dynamic) → Confusion during rate engine wiring → Potential wrong rates in production
4. **HIGH.4:** Challenge codes never generated → Photo verification always fails → Borrowers can't complete application
5. **HIGH.5:** Glossary endpoint missing → Plain language reasons test (Test 7) fails → Borrowers see code names instead of plain English

**If Unfixed, Medium Findings Will Cause:**
1. **MEDIUM.1:** Tranche eligibility rule ambiguous → Wrong tranches released → Borrowers get unapproved amounts
2. **MEDIUM.2:** Load test config incomplete → Metrics unreliable → Unsure if system handles 100 users

---

## Recommendations

1. **Priority 1 (HIGH findings):** Resolve all before starting implementation
   - Clarify tier assignment logic with explicit AND/OR rules
   - Implement photo verification invocation
   - Define rate adapter contract and storage
   - Implement challenge code generation and storage
   - Define glossary endpoint schema and sync mechanism

2. **Priority 2 (MEDIUM findings):** Resolve before testing phase
   - Clarify tranche eligibility rules
   - Finalize load test data generation and baseline metrics

3. **Priority 3 (NIT findings):** Optional improvements
   - Add error flow diagram
   - Cross-check glossary with frontend

---

## Sign-Off

**Review Status:** CHANGES_REQUESTED  
**Count of Findings:**
- HIGH: 5 (must fix)
- MEDIUM: 2 (should fix)
- NIT: 2 (optional)

**Next Step:** Author revises design, addresses all HIGH and MEDIUM findings, resubmits for second review.
