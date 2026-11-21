# Phase 1 Implementation Review: Tiered Verification-First Foundation

Phase 1 successfully establishes the core data model, business logic engines, and workflows for a verification-first, tier-based lending system. The implementation replaces generic risk scoring with explainable tier assignment, photo-backed location verification, and multi-tranche release gates.

**Watch for:** 16 test failures in old endpoint tests (Decision model fields changed), 59% overall coverage (concentrated in Phase 1 engines at >90%). Not all endpoints fully wired to new engines yet. See Issues section for details.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The data model now supports tiered lending with strong evidence sources (AA bank data, GST filings, geo-tagged photos) and weak evidence (owner-uploaded bills). Tier assignment is explainable: a Tier 1 borrower sees reasons like "verified 10 months of bank data" and "AA and UPI agree 82%", not a black-box score.

Photo verification combines geolocation extraction (EXIF) with manual code verification (OCR stub). Location is validated against rent agreement address within 500m tolerance. This prevents staging attacks and grounds lending in real shop data.

Source agreement replaces the generic ABCA engine with weighted ranking: AA at 60% (most reliable), GST at 30%, UPI at 10%. Agreement score measures how well sources align (0-1 scale). Verified window calculates the overlap period where two or more sources have data; only months in that window count for tenure requirements and weight scaling.

Tier rules are hard thresholds tied to concrete evidence. Tier 1 requires 6+ months verified data, 70%+ agreement, photo verification, and no GST registration. Tier 2 needs 12 months with GST. Tier 3 needs 24 months plus Udyam registration and prior repayment history. These rules are not tunable per-application; they're policy.

Amount calculation scales a tier cap by two factors: verification weight (how many verified months vs the tier minimum) and agreement weight (the agreement score itself). A Tier 1 with 10 months (min 6) and 82% agreement gets 50K × 1.0 × 0.82 = 41K. GST discrepancies apply a 15% penalty.

Rate is industry rate plus tier adjustment: industry_rate + 4% for Tier 1, +2% for Tier 2, +0% for Tier 3. Industry rates are stored in a rate environment table and updated separately.

Tranches split approved amount by tier: Tier 1 gets 100% now, Tier 2 gets 60% now + 40% at day 60, Tier 3 gets 40/30/20/10 at intervals. Next tranche eligibility requires all prior EMIs paid on-time. Stop rule freezes if 2+ EMIs are missed. Officer review required to unfreeze.

---

<details>
<summary>Issues (8)</summary>

1. **Decision model schema mismatch** — Existing tests expect loan_amount, rate_percent, emi_monthly fields (Stage 2 schema). Decision model was updated correctly but 16 tests still use old schema, causing TypeErrors. Tests in test_models.py, test_scoring.py, test_audit.py need updating or removal. **confirmed**

2. **Scoring endpoint wiring incomplete** — `/api/scoring/score` endpoint exists but doesn't orchestrate all 9 Phase 1 engines. Current implementation uses old pipeline. Should run source agreement → verified window → photo verification → GST coverage → tier assignment → amount rule → rate calculation → tranche plan in sequence. **likely** (verified by endpoint file review)

3. **Tranche and repayment endpoints missing implementation** — `/api/applications/{id}/tranches`, `/api/applications/{id}/repayment` endpoints are stubs or missing. Tranche eligibility check and EMI recording need database queries + Stop Rule Engine invocation. **confirmed** (files exist but mostly empty)

4. **Stop Rule Engine not invoked by repayment endpoint** — Repayment endpoint should call StopRuleEngine after recording missed EMI, but no integration visible. Frozen tranches never checked before release. **likely**

5. **Photo Verification Engine: OCR logic is stub** — `verify_code_presence()` function is placeholder. Actual handwritten code verification from uploaded photos needs ML/OCR service or manual officer review. Current implementation checks if `expected_code in photo_data`, which is mock logic. **confirmed** (visible in photo_verification_engine.py line 70-90)

6. **Rate Adapter database layer not used by endpoints** — RateAdapter has `get_industry_rate(tier)` but endpoints don't call it. Industry rates default to hardcoded values instead of querying RateEnvironment table. **confirmed** (rate_calculation_engine.py lines 15-25 hardcodes rates)

7. **Plain language layer missing** — Tier assignment engine returns structured reasons list (e.g., "verified_months_below_6") but frontend-friendly text ("We need at least 6 months of bank data") not generated. Should convert from codes to plain text for borrower display. **likely**

8. **Test coverage concentrated in engines, not orchestration** — ~200 tests pass for individual engines (source agreement 19/19, tier assignment 23/23) but scoring endpoint tests fail. Integration between engines (full decision pipeline) not tested. Coverage overall 59% but endpoints only 16-43%. **confirmed** (coverage report shows engine coverage 90%+ but endpoints 16-43%)

</details>

---

<details>
<summary>Details</summary>

### Database Schema: 10 Tables, Full Relationships

All 10 Phase 1 models are created with proper foreign keys and cascade deletes. Decision model correctly replaced loan_amount/rate_percent/emi_monthly with tier/verified_months/source_agreement_score/photo_count/tranche_plan_json. Tier table stores per-tier policies. Photo table supports multi-photo applications with EXIF geolocation and verification status. SourceAgreement, VerifiedWindow, GSTCoverage tables track calculation results. Tranche table stores multi-tranche schedule. RepaymentRecord tracks individual EMI status. StopRule enforces freeze on 2+ missed EMIs. LocationVerification stores distance between photo and rent address. RateEnvironment maintains rate history by tier.

The schema change is breaking for existing test code expecting old Decision fields, but the ORM queries are correct — the schema itself is sound. **confirmed**

### Photo Verification: Geolocation Works, OCR Stubbed

PhotoVerificationEngine correctly extracts EXIF location using Haversine formula for distance calculation. Test coverage at 97% confirms location extraction and distance matching work (within 500m tolerance). Code verification logic is stubbed: `verify_code_presence()` checks if expected_code appears in photo_data string, which is mock behavior. Real implementation needs OCR or manual officer review. Current approach passes tests but won't work in production with actual image files. Tests use mock photo_data strings, not real images. **confirmed**

### Source Agreement: Weighted Correlation Correct

SourceAgreementEngine calculates agreement score by correlating sources when 3 present, using coefficient of variation when 2 present, returning 0.5 (low confidence) when only 1. Weighted sales correctly applies AA 60% + GST 30% + UPI 10% weights. Test coverage 93% validates all branches. **confirmed**

### Verified Window: Overlap Calculation Works

VerifiedWindowEngine correctly calculates month overlap between AA + GST/UPI data ranges. Quality score based on consistency. Weight factor scales to tier minimum (e.g., 10 months / 6 month Tier 1 minimum = capped at 1.0). Tests validate edge cases (< 6 months rejected, exact boundaries). 96% coverage confirms logic is solid. **confirmed**

### Tier Assignment: Rules Explicit, Progression Clear

TierAssignmentEngine has hardcoded policy for each tier: Tier 1 needs 6+ months AA+UPI, no GST, agreement >0.7, photo verified. Tier 2 needs 12+ months AA+GST, agreement >0.65. Tier 3 needs 24+ months + Udyam + prior repayment. Returns tier + reasons + next-tier criteria. Logic checks are sequential and mutually exclusive. 96% coverage validates all paths. Returns clear reasons (e.g., "Verified 10 months of bank data (requires 6+)") and next-tier guidance ("Register for GST to qualify for Tier 2"). **confirmed**

### Amount Rule: Scaling Factors Applied Correctly

AmountRuleEngine applies formula: tier_cap × verified_weight × agreement_weight × gst_penalty. Tier caps hardcoded: Tier 1 ₹50K, Tier 2 ₹250K, Tier 3 ₹1M. Verified weight = min(verified_months / tier_min_months, 1.0). Agreement weight = source_agreement_score. GST penalty 0.85 if coverage flagged, 1.0 otherwise. Example calculation traced: Tier 1, 10 months, 0.82 agreement, no GST flag = 50K × 1.0 × 0.82 × 1.0 = 41K. **confirmed**

### Rate Calculation: Hardcoded Rates, Not Using Adapter

RateCalculationEngine has TIER_RATES hardcoded (14.5%, 12.0%, 10.5%) instead of querying RateEnvironment table. Tier adjustments correct (+4%, +2%, +0%). Tests pass because they mock rates, but integration with rate_adapter is missing. RateAdapter class exists with `get_industry_rate()` and `set_industry_rates()` methods, but no endpoint calls it and engines don't use it. **confirmed**

### Tranche Plan: Schedules Correct by Tier

TranchePlanEngine generates schedules: Tier 1 single 100%, Tier 2 two tranches 60/40 at day 0/60, Tier 3 four tranches 40/30/20/10 at day 0/60/120/180. Calculations correct. Tests validate tranche amounts sum to approved amount. **confirmed**

### Tranche Rule & Stop Rule: Logic Correct, Not Integrated

TrancheRuleEngine checks if all prior tranche EMIs paid on-time before releasing next. StopRuleEngine counts missed EMIs and freezes if >= 2. Both engines have correct logic and tests pass. But repayment endpoints don't invoke either. When EMI recorded as missed, StopRuleEngine should be called to potentially freeze. When next tranche eligibility checked, TrancheRuleEngine should be called. **likely**

### Scoring Endpoint: Old Pipeline Not Replaced

`POST /api/scoring/score` endpoint still uses old logic: run ABCA → household surplus → capacity model → loan rules → rate → EMI schedule. Should be: source agreement → verified window → photo verification → GST coverage → tier assignment → amount rule → rate calculation → tranche plan. Current implementation doesn't invoke Phase 1 engines. New decision output format not generated. **likely** (verified by endpoints/scoring.py review)

### Tranche Endpoints: Stubs Present, Not Wired

`GET /api/applications/{id}/tranches` returns list but no eligibility checks. `POST /api/applications/{id}/tranches/{num}/approve` exists but doesn't invoke TrancheRuleEngine or update tranche release status. Repayment endpoints store EMI records but don't invoke StopRuleEngine. **confirmed**

### Photo Endpoints: Upload Path Exists, Verification Not Invoked

`POST /api/applications/{id}/photos` saves photo metadata but doesn't call PhotoVerificationEngine. Photo verification status stays "pending" forever. Officer must manually verify or verification skipped entirely. **confirmed**

### Tests: Engines Solid (90%+ coverage), Integration Broken (16% failures)

Individual engine tests pass: source agreement 19/19, tier assignment 23/23, photo verification 12/12, verified window 16/16, GST coverage 20/20. But endpoint integration tests fail because Decision model schema changed and old scoring tests use obsolete fields. Total: 457 passing, 16 failing. Old test suite expects `Decision.loan_amount` but that field is gone. Tests need removal (Stage 2 endpoints deprecated) or rewriting (Stage 2 endpoints still used). **confirmed**

### Coverage Concentrated in Engine Logic

Phase 1 engines: >90% coverage. Photo verification 97%, verified window 96%, tier assignment 96%, source agreement 93%. Rate calculation engine 67% (missing edge cases). Tranche rule engine 38% (incomplete testing). Overall app coverage 59% but broken down: engines 90%+, endpoints 16-43% (old tests fail), models 100% (new schema only). Phase 1 success metric is >85%, which is met for core logic but inflated by incomplete endpoint coverage. **confirmed**

### Capacity Model References Removed, Old Engines Not Removed

Decision model no longer has capacity fields. Capacity engine file still exists but unused by Phase 1. ABCA engine file still exists but replaced by source agreement engine. Old loan_rules_engine, emi_engine files exist but Phase 1 doesn't use them. No harm (dead code doesn't break), but codebase has both old and new engines. Cleanup recommended in Phase 2. **confirmed**

</details>

---

## File map

**Models & Schema:**
- `app/models.py` — Added 10 new tables (Tier, Photo, SourceAgreement, VerifiedWindow, GSTCoverage, Tranche, RepaymentRecord, StopRule, LocationVerification, RateEnvironment). Updated Decision model to replace loan_amount/rate_percent/emi_monthly with tier/verified_months/source_agreement_score/location_verified/photo_count/tranche_plan_json.

**Adapters:**
- `app/adapters/rate_adapter.py` — Industry rate lookup by tier. Not integrated into endpoints yet.

**Phase 1 Engines:**
- `app/engines/photo_verification_engine.py` — EXIF geolocation, distance calculation, code verification (stubbed OCR).
- `app/engines/source_agreement_engine.py` — Compare AA/GST/UPI with weighted scoring.
- `app/engines/verified_window_engine.py` — Calculate overlapping data period and quality score.
- `app/engines/gst_coverage_engine.py` — Reconcile purchases to GST turnover, flag discrepancies.
- `app/engines/tier_assignment_engine.py` — Assign Tier 1/2/3 with rules and next-tier criteria.
- `app/engines/amount_rule_engine.py` — Scale tier cap by verification and agreement weights.
- `app/engines/rate_calculation_engine.py` — Industry rate + tier adjustment (hardcoded rates, not using adapter).
- `app/engines/tranche_plan_engine.py` — Generate multi-tranche schedule by tier.
- `app/engines/tranche_rule_engine.py` — Check next-tranche eligibility (all prior EMIs on-time).
- `app/engines/stop_rule_engine.py` — Freeze tranches on 2+ missed EMIs.

**Endpoints:**
- `app/endpoints/scoring_phase1.py` — New scoring endpoint (created but not integrated with main scoring).
- `app/endpoints/tranches.py` — Tranche list/detail (partial implementation).
- `app/endpoints/repayment.py` — Repayment tracking (stubs present, missing Stop Rule invocation).
- `app/endpoints/photos.py` — Photo upload (stub, doesn't invoke Photo Verification Engine).

**Tests:**
- `tests/test_phase1_*.py` — 14 test files covering all 9 Phase 1 engines + models + adapters. ~170 Phase 1 specific tests passing. Old endpoint tests (test_scoring.py, test_audit.py, test_models.py) have 16 failures due to Decision schema change.

**Documentation:**
- `PHASE_1_IMPLEMENTATION_SUMMARY.md` — Overview of all 10 models and 9 engines.
- `PHASE_1_TEST_SUITE_COMPLETE.md` — Test coverage breakdown (169 Phase 1 tests passing).
- `PHASE_1_2_IMPLEMENTATION_CHECKLIST.md` — Detailed task list and completion status.

See full diff at `git log --oneline HEAD~9..HEAD`.

