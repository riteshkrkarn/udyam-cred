# Phase 1-2 Implementation Checklist

**Status:** IN PROGRESS
**Started:** 2024-11-20
**Target Completion:** Phase 1: 2024-12-04, Phase 2: 2024-12-11

## Phase 1: Foundation (Weeks 1-2) ~5 days

### Database Schema (Task 1.1)
- [x] Review existing models.py
- [x] Plan new tables (Tier, Photo, SourceAgreement, VerifiedWindow, GSTCoverage, Tranche, RepaymentRecord, StopRule, LocationVerification, RateEnvironment)
- [ ] Update Decision model (remove loan_amount, rate_percent, emi_monthly; add tier, verified_months, source_agreement_score, location_verified, photo_count, tranche_plan_json)
- [ ] Add Tier table with relationships
- [ ] Add Photo table with GIS capabilities  
- [ ] Add SourceAgreement, VerifiedWindow, GSTCoverage tables
- [ ] Add Tranche, RepaymentRecord, StopRule tables
- [ ] Add LocationVerification, RateEnvironment tables
- [ ] Create database migration script
- [ ] Write model tests (20 tests) ✓ TESTS CREATED

### Rate Adapter (Task 1.2)
- [ ] Create `app/adapters/rate_adapter.py`
- [ ] Implement `get_industry_rate(tier: int)`
- [ ] Implement `set_industry_rates()`
- [ ] Add fallback rates
- [ ] Write tests (5 tests) ✓ TESTS CREATED

### Photo Verification Engine (Task 1.3)
- [ ] Create `app/engines/photo_verification_engine.py`
- [ ] Implement photo validation (format, size)
- [ ] Implement geo-location extraction
- [ ] Implement location matching (photo vs rent address)
- [ ] Implement code verification logic
- [ ] Write tests (12 tests) ✓ TESTS CREATED

### Source Agreement Engine (Task 1.4)
- [ ] Create `app/engines/source_agreement_engine.py` (replace abca_engine.py)
- [ ] Implement correlation calculation (AA vs GST vs UPI)
- [ ] Implement weighted average calculation
- [ ] Implement confidence scoring
- [ ] Write tests (15 tests) ✓ TESTS CREATED

### Verified Window Engine (Task 1.5)
- [ ] Create `app/engines/verified_window_engine.py`
- [ ] Calculate verified data window (month overlap)
- [ ] Calculate data quality score
- [ ] Calculate weight factor for amount scaling
- [ ] Write tests (10 tests) ✓ TESTS CREATED

### GST Coverage Engine (Task 1.6)
- [ ] Create `app/engines/gst_coverage_engine.py`
- [ ] Calculate coverage % (GST turnover / purchases)
- [ ] Implement reconciliation flagging
- [ ] Write tests (8 tests) ✓ TESTS CREATED

### Tier Assignment Engine (Task 1.7)
- [ ] Create `app/engines/tier_assignment_engine.py`
- [ ] Implement Tier 1 logic (6mo AA+UPI, no GST, no Udyam)
- [ ] Implement Tier 2 logic (12mo AA+GST or 12mo AA+UPI with GST registered)
- [ ] Implement Tier 3 logic (24mo AA+GST, Udyam, prior repayment)
- [ ] Return tier + reasons + next-tier criteria
- [ ] Write tests (20 tests) ✓ TESTS CREATED

### Amount Rule Engine (Task 1.8)
- [ ] Create `app/engines/amount_rule_engine.py`
- [ ] Implement tier cap logic
- [ ] Implement verification weight scaling
- [ ] Implement agreement weight scaling
- [ ] Write tests (15 tests) ✓ TESTS CREATED

### Rate Calculation Engine (Task 1.9)
- [ ] Create `app/engines/rate_calculation_engine.py`
- [ ] Fetch industry rate by tier
- [ ] Apply tier adjustment
- [ ] Calculate final APR
- [ ] Write tests (8 tests) ✓ TESTS CREATED

### Tranche Plan Generator (Task 1.10)
- [ ] Create `app/engines/tranche_plan_engine.py`
- [ ] Tier 1: 1 tranche (100% now)
- [ ] Tier 2: 2-3 tranches (60% now, 40% at +60d)
- [ ] Tier 3: 4 tranches (40%, 30%, 20%, 10% at intervals)
- [ ] Write tests (12 tests) ✓ TESTS CREATED

### Tranche Rule Engine (Task 1.11)
- [ ] Create `app/engines/tranche_rule_engine.py`
- [ ] Check if next tranche eligible (all prior EMIs on-time)
- [ ] Return eligibility + reason + release date
- [ ] Write tests (10 tests) ✓ TESTS CREATED

### Stop Rule Engine (Task 1.12)
- [ ] Create `app/engines/stop_rule_engine.py`
- [ ] Freeze on 2+ missed EMIs
- [ ] Flag for review
- [ ] Return freeze reason
- [ ] Write tests (8 tests) ✓ TESTS CREATED

### Update Scoring Endpoint (Task 1.13)
- [ ] Modify `POST /api/scoring/score` endpoint
- [ ] Replace old logic with new pipeline:
  - Fetch AA, GST, UPI
  - Source Agreement Engine
  - Verified Window Engine
  - Photo Verification Engine
  - GST Coverage Engine
  - Tier Assignment Engine
  - Amount Rule Engine
  - Rate Calculation Engine
  - Tranche Plan Generator
  - EMI calculations
- [ ] Return new output format (tier, tranche_plan, reasons)
- [ ] Write tests (50 tests) ✓ TESTS CREATED

### Tranche Endpoints (Task 1.14)
- [ ] Create `app/endpoints/tranche.py`
- [ ] `GET /api/applications/{id}/tranches`
- [ ] `GET /api/applications/{id}/tranches/{tranche_num}`
- [ ] `POST /api/applications/{id}/tranches/{tranche_num}/approve`
- [ ] `GET /api/applications/{id}/tranches/{tranche_num}/eligibility`
- [ ] Write tests (10 tests) ✓ TESTS CREATED

### Repayment Endpoints (Task 1.15)
- [ ] Create `app/endpoints/repayment.py`
- [ ] `GET /api/applications/{id}/repayment`
- [ ] `POST /api/applications/{id}/repayment/record`
- [ ] `GET /api/applications/{id}/repayment/next-emi`
- [ ] `GET /api/audit/repayment-monitor`
- [ ] Write tests (15 tests) ✓ TESTS CREATED

### Photo Endpoints (Task 1.16)
- [ ] Create `app/endpoints/photos.py`
- [ ] `POST /api/applications/{id}/photos`
- [ ] `GET /api/applications/{id}/photos`
- [ ] `GET /api/applications/{id}/photos/{photo_id}`
- [ ] Write tests (10 tests) ✓ TESTS CREATED

### Phase 1 Tests (Task 1.17)
- [ ] Write all unit tests for engines (120 tests)
- [ ] Write endpoint tests (50 tests)
- [ ] Write integration tests (30 tests)
- [ ] **Total:** ~200 tests
- [ ] **Coverage:** >85%
- [ ] Test models (20)
- [ ] Test adapters (5)
- [ ] Test photo_verification (12)
- [ ] Test source_agreement (15)
- [ ] Test verified_window (10)
- [ ] Test gst_coverage (8)
- [ ] Test tier_assignment (20)
- [ ] Test amount_rule (15)
- [ ] Test rate_calculation (8)
- [ ] Test tranche_plan (12)
- [ ] Test tranche_rule (10)
- [ ] Test stop_rule (8)

## Phase 2: Polish & Refinement (Weeks 3-4) ~4 days

### Data Validation (Task 2.1)
- [ ] Create `app/validators/` directory
- [ ] `validate_application()`
- [ ] `validate_tier_assignment()`
- [ ] `validate_tranche_plan()`
- [ ] `validate_repayment()`
- [ ] Write tests (25 tests)

### Error Handling (Task 2.2)
- [ ] Create `app/utils/error_handler.py`
- [ ] Exception hierarchy
- [ ] Structured logging
- [ ] User-friendly error messages
- [ ] Error tracking setup
- [ ] Write tests (20 tests)

### Plain Language Layer (Task 2.3)
- [ ] Create `app/templates/reasons.py`
- [ ] TIER_REASONS dictionary
- [ ] NEXT_TIER_REASONS dictionary
- [ ] `generate_plain_reasons()` function
- [ ] Write tests (15 tests)

### Glossary & Help (Task 2.4)
- [ ] Create `app/templates/glossary.py`
- [ ] Define all 10+ terms
- [ ] Add examples for each
- [ ] Write tests (5 tests)

### Audit Trail Enhancement (Task 2.5)
- [ ] Extend `AuditLog` model
- [ ] Log all application actions
- [ ] Log all scoring/tier/tranche changes
- [ ] Write tests (15 tests)

### Officer Dashboard (Task 2.6)
- [ ] Create `app/endpoints/dashboard.py`
- [ ] `GET /api/dashboard/queue`
- [ ] `GET /api/dashboard/repayment-status`
- [ ] `GET /api/dashboard/stats`
- [ ] `GET /api/dashboard/alerts`
- [ ] Write tests (12 tests)

### Synthetic Data Update (Task 2.7)
- [ ] Update `synth/generator.py`
- [ ] Generate Tier-appropriate data
- [ ] Generate synthetic repayment history
- [ ] Generate tranche release data
- [ ] Write tests (10 tests)

### Golden Test Cases (Task 2.8)
- [ ] Create `tests/golden_expected_phase2.csv`
- [ ] Test all 10 scenarios (approval, rejection, tranches, stop rules, replay, overrides)
- [ ] Write tests (10 tests)

### E2E Integration Tests (Task 2.9)
- [ ] Create `tests/test_integration_phase2_e2e.py`
- [ ] Tier 1 full journey
- [ ] Tier 2 full journey
- [ ] Stop rule trigger
- [ ] Officer workflow
- [ ] Write tests (20 tests)

### API Documentation (Task 2.10)
- [ ] Create `API_DOCS_PHASE2.md`
- [ ] Document all new endpoints
- [ ] Document schemas
- [ ] Document tier logic
- [ ] Document rate calc
- [ ] Document tranche gates
- [ ] Document stop rules

### Migration Guide (Task 2.11)
- [ ] Create `MIGRATION_STAGE2_TO_PHASE2.md`
- [ ] Database migration steps
- [ ] Breaking API changes
- [ ] Deprecations
- [ ] Backward compatibility plan

### Phase 2 Tests (Task 2.12)
- [ ] Validation tests (25)
- [ ] Error handling tests (20)
- [ ] Plain language tests (15)
- [ ] Glossary tests (5)
- [ ] Audit trail tests (15)
- [ ] Dashboard tests (12)
- [ ] Synthetic data tests (10)
- [ ] Golden cases tests (10)
- [ ] E2E tests (20)
- [ ] **Total:** ~130 tests
- [ ] **Coverage:** >85%

## Summary Statistics

| Phase | Duration | Tables | Engines | Endpoints | Tests | Coverage |
|-------|----------|--------|---------|-----------|-------|----------|
| Phase 1 | Weeks 1-2 | 10 | 9 | 9 | 200+ | >85% |
| Phase 2 | Weeks 3-4 | 0 | 0 | 5 | 130+ | >85% |
| **Total** | **4 weeks** | **10** | **9** | **14** | **330+** | **>85%** |

## Success Criteria

**Phase 1 Complete When:**
- ✓ All 10 new tables created with constraints
- ✓ All 9 engines implemented and tested
- ✓ All 9 endpoints working
- ✓ 200+ tests passing
- ✓ >85% code coverage
- ✓ Tier assignment working for all scenarios
- ✓ Tranche generation and tracking working
- ✓ Stop rule enforcing correctly
- ✓ Photo verification working
- ✓ Source agreement calculation correct

**Phase 2 Complete When:**
- ✓ All validation in place
- ✓ Error handling comprehensive
- ✓ Plain language generated correctly
- ✓ Officer dashboard working
- ✓ 130+ tests passing
- ✓ All golden cases passing
- ✓ E2E flows all working
- ✓ Documentation complete
- ✓ Migration guide ready
- ✓ System production-ready

## Next Step
Start Phase 1 implementation with Task 1.1 (Database Schema Refactor)

