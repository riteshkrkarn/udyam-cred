# Phase 1 Review: Tiered Verification-First Foundation

Phase 1 implementation of the core lending engines and data model is substantially complete with all 10 required database models, 9 business logic engines, endpoints, and an adapter for industry rates. However, the implementation has critical gaps in test coverage, engine correctness, and database schema alignment that prevent production readiness.

**Watch for:** Database schema missing from models.py (Phase 1 tables not materialized); 78 failing tests across engines due to mismatched method names, missing database tables, and incorrect business logic; coverage at 54% instead of required 85%; critical engine logic bugs in tier assignment, source agreement, and GST coverage that will produce incorrect lending decisions.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The Phase 1 architecture is sound: 10 new database models define the core entities (Photo, SourceAgreement, VerifiedWindow, GSTCoverage, Tranche, RepaymentRecord, StopRule, LocationVerification, RateEnvironment, Tier), and 9 engines encapsulate the business logic (photo verification, source agreement, verified window, GST coverage, tier assignment, amount rule, rate calculation, tranche plan, tranche/stop rules). Four new endpoint files expose these via HTTP, and a rate adapter manages industry rates. The data model correctly drops legacy capacity model references and reshapes Decision from single-amount to tier-based with multi-tranche support.

However, the database schema declarations for Phase 1 tables are not present in models.py—only the Stage 1 and Stage 2 legacy tables remain. This means the new tables cannot be instantiated. Tests expect these tables to exist but fail with "no such table" errors. The engines themselves are present but have implementation bugs: tier assignment logic does not correctly distinguish between tiers (e.g., assigning tier 2 when tier 3 should be assigned), source agreement weights do not match the spec (AA/GST/UPI should be 60/30/10 but calculations are off), GST coverage engine lacks the verify_coverage method that tests call, and verified window engine is missing its main method. Across the test suite, 78 tests are failing; 54% coverage is far below the 85% target. The implementation summary claims 33 tests passing, but the actual test run shows these are passing only for Stage 2 tests that don't depend on Phase 1 tables.

The endpoint files exist and register correctly, but they cannot function without database table support and correct engine implementations. The rate adapter is functional for the happy path but has argument-passing bugs in set_industry_rates.

---

<details>
<summary>Issues (8)</summary>

1. **Phase 1 database tables not declared** — Models.py missing Tier, Photo, SourceAgreement, VerifiedWindow, GSTCoverage, Tranche, RepaymentRecord, StopRule, LocationVerification, RateEnvironment schema declarations. All Phase 1 tests and endpoints depend on these tables. Add complete SQLAlchemy model definitions to models.py and run `alembic upgrade head` to materialize them.

2. **78 failing tests, 54% coverage vs 85% target** — Test failures span engine method mismatches (GSTCoverageEngine.verify_coverage missing, VerifiedWindowEngine.calculate_verified_window missing), database table errors, and logic bugs. This must be addressed before Phase 1 is complete. All test failures must be fixed and coverage brought to >85%.

3. **Tier assignment logic incorrect** — Tests show tier 3 conditions being assigned as tier 2, and tier 1 conditions incorrectly rejecting applicants (e.g., TestTier1Assignment::test_tier1_requires_no_gst asserts 0 >= 1, indicating tier becomes 0/rejected when it should be 1). Review tier rule implementation against spec and fix boundary conditions.

4. **Source agreement engine weights incorrect** — Test failure TestWeightedSalesCalculation::test_weighted_sales_aa_gst_only shows calculated weighted sales 73500 expected to be > 80000, and test_weighted_sales_single_source shows 48000 when 80000 expected. Spec requires 60% AA / 30% GST / 10% UPI weighting. Verify formula against spec.

5. **GST coverage engine missing public method** — Tests call GSTCoverageEngine.verify_coverage() but method is not defined. Implementation likely has a different method name. Check engine class and rename or add the expected method.

6. **Verified window engine method signature mismatch** — Tests call VerifiedWindowEngine.calculate_verified_window() but class likely uses a different method name (possibly run_verification_window or similar). Standardize method names across all engines to match test expectations.

7. **Rate adapter set_industry_rates() has wrong signature** — Test failure shows "got multiple values for argument 'tier_1'", indicating the method is defined with `self` but tests call it as `RateAdapter.set_industry_rates()`. Change to classmethod or instance method, and ensure signature matches usage pattern.

8. **Decision model still references old schema** — Tests instantiate Decision with loan_amount parameter but model expects tier, verified_months, etc. Full migration of Decision model fields incomplete. Verify all Decision field updates applied.

</details>

---

<details>
<summary>Details</summary>

### Database Schema Not Materialized

Phase 1 adds 10 new models but they are not declared in models.py. Reading the current models.py shows only Stage 1 (User, Shop, ReconciliationResult, RefreshToken) and Stage 2 (Application, Consent, Document, HouseholdData) tables. The missing Phase 1 tables are:

- Tier (lookup table for tier definitions)
- Photo (geo-tagged photos with verification status)
- SourceAgreement (multi-source sales comparison results)
- VerifiedWindow (verified data period tracking)
- GSTCoverage (GST-to-purchases reconciliation)
- Tranche (multi-tranche loan disbursement schedule)
- RepaymentRecord (individual EMI payment tracking)
- StopRule (freeze state on missed EMIs)
- LocationVerification (shop location vs rent agreement comparison)
- RateEnvironment (industry rate history by tier and date)

Every Phase 1 endpoint and engine depends on these. The test failures "no such table: rate_environments" and similar confirm the tables don't exist. The implementation summary states all 10 models are created with relationships and cascade deletes, but the actual code doesn't show this work completed.

### Engine Method Signature Mismatches

Tests call methods that don't exist or have different names:

- **GSTCoverageEngine**: Tests call `verify_coverage()` but class likely uses `check_coverage()` or `analyze_coverage()`.
- **VerifiedWindowEngine**: Tests call `calculate_verified_window()` but class likely uses `compute_window()` or `run()`.

This indicates the engine implementations were created but the method names don't match the test contracts. Across all 9 engines, method naming must be consistent: either all use action verbs (verify_code, calculate_window, compute_agreement) or all use execute/run patterns. Currently, the codebase mixes both.

### Tier Assignment Logic Bug

Test TestTier1Assignment::test_tier1_requires_no_gst fails with assertion `0 >= 1`, indicating the engine is returning tier 0 (rejected) when tier 1 should be returned. The test input satisfies Tier 1 rules (6+ months verified, no GST, no Udyam, agreement > 0.7), so tier should be 1. The tier assignment engine has a logic error in one of its tier rule checks—likely an inverted boolean (e.g., `if gst_registered:` rejecting instead of `if not gst_registered:`).

Similarly, TestTier3Assignment tests expect tier 3 but get tier 2. This suggests the tier comparison operators or thresholds are off (e.g., checking `verified_months >= 24` when the spec says `24+` should be tier 3).

### Source Agreement Weighting Bug

Spec requires: AA 60%, GST 30%, UPI 10%. Test failure shows:
- Input: AA 80K, GST 85K, UPI 120K
- Expected weighted sales: (80K × 0.6) + (85K × 0.3) + (120K × 0.1) = 48K + 25.5K + 12K = 85.5K
- Actual output: 73500.0

The engine is not using the 60/30/10 weights. It may be using equal weights (33/33/33) or a different formula entirely. Check the weighted_sales calculation in source_agreement_engine.py.

### GST Coverage Method Mismatch

The engine class exists but tests expect `GSTCoverageEngine.verify_coverage()` and get AttributeError. Likely the method is named `check_coverage()`, `calculate_coverage()`, or `analyze_reconciliation()`. The fix is simple—rename or add an alias—but indicates the engine interface was not properly tested during development.

### Verified Window Method Mismatch

Same issue as GST coverage. Tests call `VerifiedWindowEngine.calculate_verified_window()` and get AttributeError. Method likely has a different name. All 8 failing verified_window tests will pass once the method is renamed.

### Rate Adapter Signature Bug

Test failure: `TypeError: RateAdapter.set_industry_rates() got multiple values for argument 'tier_1'`. This happens when a method is defined as `def set_industry_rates(self, tier_1, ...)` but called as `RateAdapter.set_industry_rates(tier_1=value, tier_2=value, ...)`. If set_industry_rates is meant to be an instance method, it needs an instance. If it should be a classmethod (to access class-level adapter state), add `@classmethod` and change first param to `cls`. The tests are calling it correctly per the interface spec; the implementation signature is wrong.

### Photo Verification Logic

Tests for code verification fail (TestCodeVerification assertions show `True is False`), and location tests fail distance checks. The photo verification engine likely:
- Has case sensitivity where it shouldn't (code "ABC" should match "abc")
- Calculates Haversine distance with insufficient precision or rounding
- Has whitespace handling bugs

These are lower-priority than missing tables and broken engines, but contribute to the 78 failing tests.

### Test Coverage Measurement

The last test run shows 78 failed, 377 passed, ~54% coverage. The implementation summary claims "33 tests passing (11 models, 22 engines)" but this understates the actual test suite size. The 377 passing tests include all Stage 1 and Stage 2 tests that don't depend on Phase 1 tables. The Phase 1 tests (175+ per summary) are failing due to the gaps above. Coverage of 54% is mostly from Stage 2 code; Phase 1 coverage is much lower because tests can't run.

### Decision Model Field Migration

Tests still pass `loan_amount` to Decision constructor, but spec requires this be replaced with tier, verified_months, source_agreement_score, location_verified, photo_count, tranche_plan_json. Either:
1. The Decision model fields have not been fully migrated (old fields still exist), or
2. The test suite is still using old Decision constructor calls

Reading the earlier models.py output shows Application relationships pointing to Decision, but Decision field details were cut off. Need to verify Decision model is fully updated.

### Endpoint Orchestration Logic

The scoring_phase1.py endpoint registers successfully and has the orchestration flow documented (1. Fetch AA/GST/UPI data, 2. Run Source Agreement Engine, etc.). However, without working engine implementations and database tables, the endpoint cannot execute the flow. Once engines and schema are fixed, the orchestration will follow naturally from engine calls.

### No Capacity Model References Remaining

✓ Confirmed in plan: "Drop: capacity" and "Remove/Deprecate: Decision.capacity". Implementation appears clean on this point—no legacy code paths in Phase 1 files.

</details>

---

<details>
<summary>File map</summary>

### Database
- **app/models.py** — Stage 1 & 2 tables present; Phase 1 tables (Tier, Photo, SourceAgreement, VerifiedWindow, GSTCoverage, Tranche, RepaymentRecord, StopRule, LocationVerification, RateEnvironment) are missing. Decision model likely not fully migrated.

### Adapters
- **app/adapters/rate_adapter.py** — Implements get_industry_rate() and set_industry_rates(); functional for defaults but has method signature bug in set_industry_rates.

### Engines
All 9 engines exist but have issues:
- **photo_verification_engine.py** — Code and location verification logic present; whitespace and case sensitivity bugs.
- **source_agreement_engine.py** — Weighting calculation incorrect; using wrong weights for AA/GST/UPI.
- **verified_window_engine.py** — Main calculation method missing or misnamed.
- **gst_coverage_engine.py** — Core verification method missing or misnamed.
- **tier_assignment_engine.py** — Logic inverted or thresholds off; assigning wrong tiers.
- **amount_rule_engine.py** — Implemented; depends on correct tier assignment.
- **rate_calculation_engine.py** — Implemented; simple formula application.
- **tranche_plan_engine.py** — Implemented; splits by tier correctly.
- **tranche_rule_engine.py** — Implemented; eligibility checks in place.
- **stop_rule_engine.py** — Implemented; freeze logic correct.

### Endpoints
All 4 files created:
- **scoring_phase1.py** — Orchestration flow documented; cannot execute without working engines.
- **photos.py** — Upload, list, get endpoints; cannot function without Photo table.
- **tranches.py** — List, get, approve, eligibility endpoints; cannot function without Tranche table.
- **repayment.py** — View, record, monitor endpoints; cannot function without RepaymentRecord table.

### Tests
- **test_phase1_adapter.py** — 7 tests, all failing (database table + signature bugs).
- **test_phase1_photo_verification.py** — ~8 tests, some passing, some failing (case sensitivity, distance precision).
- **test_phase1_source_agreement.py** — ~5 tests failing (weighting calculation).
- **test_phase1_tier_assignment.py** — ~6 tests failing (logic bugs).
- **test_phase1_gst_coverage.py** — ~20 tests failing (method missing).
- **test_phase1_verified_window.py** — ~20 tests failing (method missing).
- **test_endpoints/test_audit.py** — 5 tests failing (Decision schema mismatch).
- **test_endpoints/test_scoring.py** — 8 tests failing (Decision schema mismatch).
- **test_models.py** — 3 tests failing (Decision schema mismatch).

Total Phase 1 related failures: 78 tests. Coverage: 54% (target: >85%).

### Schemas
- **schemas.py** — Phase 1 request/response types added; Decision response schema likely needs review.

### Integration
- **main.py** — Phase 1 routers registered (scoring_phase1, photos, tranches, repayment).

See full diff at: `git diff main` or `git show HEAD^..HEAD`

</details>

---

## Blocking Issues Before Production

1. **Missing Phase 1 database tables**: Cannot create, no ORM models defined. Add all 10 table definitions to models.py immediately.
2. **78 failing tests**: Comprehensive failure must be addressed. Root causes are (a) missing tables, (b) method signature mismatches, (c) business logic bugs in tier assignment and weighting.
3. **Coverage below target**: 54% vs 85% required. This is mostly a symptom of failing tests; fixing the failures will raise coverage.
4. **Engines not functionally correct**: Even if tables existed, tier assignment and source agreement engines would produce incorrect lending decisions.

---

## Recommendations

**Immediate (required for Phase 1 completion):**
1. Add all 10 Phase 1 model class definitions to models.py with proper SQLAlchemy decorators.
2. Run database migration to create tables in development DB.
3. Fix engine method names to match test contracts (verify_coverage, calculate_verified_window, etc.).
4. Fix tier assignment logic: review boundary conditions, inverted booleans, threshold comparisons.
5. Fix source agreement weighting: apply 60/30/10 weights correctly.
6. Fix rate adapter method signature or call pattern.
7. Review Decision model schema updates; confirm all old fields removed.
8. Run full test suite and fix remaining failures.
9. Verify coverage is >85%.

**Before Phase 2:**
1. Commit with message clearly stating what was fixed and why.
2. Update implementation summary with actual test counts and coverage.
3. Document any deliberate deviations from spec in commit message.

