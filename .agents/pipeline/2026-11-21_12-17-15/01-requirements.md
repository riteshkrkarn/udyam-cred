# Phase 1 & 2 Integration Testing & Production Deployment - Requirements

**Date:** 2026-11-21  
**Status:** IN PROGRESS  
**Scope:** Complete Phase 1 & 2 implementation with integration tests, security audit, load testing, and direct production deployment  
**Success Metric:** All integration tests passing, security baseline met, 100+ concurrent users supported, live in production

---

## Summary

The UdyamCred system (Phases 1-2) implements a tiered, verification-first microloan decisioning platform for Indian MSME borrowers. Phase 1 engines are mostly complete (photo verification, source agreement, tier assignment, tranche planning, repayment tracking, stop rules). Frontend and ML are feature-complete per checklists. This phase focuses on wiring all components end-to-end, validating security posture, testing production load, and deploying live.

**Key architectural decision:** Fixed pipeline (no multi-agent design). All decisions follow a deterministic rule-based flow, enabling reproducibility and auditability. Phase 1 mock OCR for photos, deterministic adapters for external data (UPI, GST, Account Aggregator). No rate limiting in v1. Direct rollout to production (no canary/phased deployment).

---

## Functional Requirements

### FR1: End-to-End Integration Testing

**FR1.1** Complete borrower workflow integration test
- Path: Create application → Consent → Photo capture (3 shots) → Document upload (electricity bill) → Household data → Scoring (all engines fire in sequence) → Result page with tier, amount, rate, EMI schedule, reasons, tranche plan → Officer approves tranche
- Validates: Frontend calls correct APIs, backend orchestrates all 9 Phase 1 engines, decision schema matches output, reasons display in plain language
- Fixtures: 1 synthetic shop with 12 months AA + UPI + GST data (Tier 2), geo-verified location, valid photo metadata
- Coverage: Happy path (success) and 5 error paths (missing consent, photo verification failure, location mismatch, insufficient data, frozen status)

**FR1.2** Officer dashboard integration test
- Path: Queue view (filter by tier, sort by date) → Click case → See tabs (overview, sources, photos, documents, repayment) → Replay with modified household data → See new scoring result → Override with reason
- Validates: Dashboard loads all applications correctly, replay engine re-scores without persisting, override reason logged to audit trail
- Fixtures: 10 applications in various tiers and states (pending, approved, frozen)
- Coverage: Happy path and 3 error paths (replay with invalid data, insufficient permissions for override, audit trail missing)

**FR1.3** Tier-driven feature validation
- Requirement (user feedback): "tier drives verified_months" — i.e., tier assignment must depend on verified data window
- Validate: Tier 1 requires 6+ verified months (AA+UPI with no GST), Tier 2 requires 12+ verified months (AA+GST or AA+UPI+GST registered), Tier 3 requires 24+ verified months (AA+GST+Udyam+prior repayment)
- Test scenarios: Exact boundary cases (5.99 months → Tier 0/reject, 6.0 months → Tier 1, etc.)

**FR1.4** Tranche gate enforcement
- Validate: First tranche released on approval, subsequent tranches only if all prior EMIs paid on-time
- Test: Apply → Release Tranche 1 → Record on-time EMI payment → Release Tranche 2 → Attempt release Tranche 3 before recording second EMI → Verify rejection
- Verify: Tranche rule engine correctly checks prior EMI history before releasing

**FR1.5** Stop rule enforcement (freeze on 2 missed EMIs)
- Validate: Application frozen when 2+ EMIs missed, appears in frozen status queue, cannot request new tranches
- Test: Create application → Release tranche → Record 1 missed EMI (show unfrozen) → Record 2nd missed EMI (freeze triggered) → Verify frozen status, verify audit log
- Verify: StopRuleEngine invoked on repayment endpoint, freeze persisted

**FR1.6** Photo verification integration
- Validate: Photo upload → EXIF extraction → Geo-location comparison (within 500m of rent address) → Challenge code verification (text/QR code detection)
- Test: 3 scenarios: (a) Valid photo (code present, location within range), (b) Code missing, (c) Location outside range
- Verify: Photo service integration with frontend camera API and backend verification logic
- Note: Photo OCR is mock (no real image processing)

**FR1.7** Plain language layer
- Validate: Tier reasons displayed to borrowers (not scores/codes)
- Example reason: "You qualify for Tier 2 because we verified 12 months of bank and sales data and your shop is registered for GST" (not "tier_2_aa_gst_verified_window_12")
- Test: All engine outputs converted to borrower-friendly text, plain language glossary available in UI
- Verify: Glossary entries match reason templates (18 terms across 6 categories per frontend checklist)

**FR1.8** ML scoring pipeline integration
- Validate: Backend deterministic rules produce decisions, ML pipeline can replay same inputs and get same outputs (for evaluation, not live scoring)
- Test: Generate 100 synthetic shops → Score in backend → Export decisions → Rescore in ML pipeline → Compare outputs (must be identical for rule-based systems)
- Verify: No stochastic elements, reproducible results

---

### FR2: Security Baseline (OWASP Top 10)

**FR2.1** Authentication & Authorization (A07:2021 Identification & Authentication)
- JWT tokens required for all endpoints (except public login/health)
- Token expiry: 15 minutes, refresh tokens rotate
- Roles: borrower (access own applications), officer (access queue + case view), auditor (read-only audit logs)
- Validate: borrower cannot access other borrower's application, officer cannot override without "approver" role
- Test: 5 scenarios per role (attempt cross-borrower access, missing token, expired token, wrong role, valid access)

**FR2.2** Data isolation & multi-tenancy (A01:2021 Broken Access Control)
- Borrower can only view/modify own applications
- Officer can view assigned queue (if role-based queue assignment implemented) or all queues (if multi-tenant not yet implemented)
- Auditor can view audit logs but not modify any data
- Database queries filtered by user_id (borrower) or role (officer/auditor)
- Test: Query filtering works at repository layer, no data leakage in API responses
- Verify: No raw borrower data in logs, responses masked

**FR2.3** Input validation & injection prevention (A03:2021 Injection)
- All endpoints use Pydantic schemas (type validation, range checks, length limits)
- Test SQL injection: application_id, shop_id, borrower_id with SQL payloads ("1 OR 1=1", "; DROP TABLE;")
- Verify: Parameterized queries, no SQL injection possible
- Test XSS: Reason text, document file names with script tags
- Verify: Output sanitized (ORM handles escaping)

**FR2.4** Sensitive data protection (A02:2021 Cryptographic Failures)
- No plaintext passwords in logs (bcrypt hashing enforced)
- No SSN, Aadhaar, account numbers in logs or audit trail (mask with "*")
- PII in documents stored encrypted or access-restricted
- Test: Attempt to log confidential data, verify masking or rejection
- Token storage: Verify HTTPOnly flag set in cookies or secure localStorage

**FR2.5** CORS & origin validation (A01:2021 CORS misconfiguration)
- Frontend origin (http://localhost:3000 for dev, production domain for prod) explicitly allowed
- OPTIONS preflight requests handled
- Test: Cross-origin request from different domain → Verify rejection

**FR2.6** File upload security (A04:2021 Insecure Deserialization, A06:2021 Vulnerable Components)
- File types: PDF, JPG, PNG only
- File size: <10MB per file
- Validate: Magic bytes (not just extension), scan for malware
- Test: Upload EXE, ZIP, JS with PDF extension → Verify rejection

**FR2.7** Error handling & information disclosure (A01:2021 Broken Access Control, A09:2021 Logging & Monitoring)
- No stack traces in API responses (500 errors return generic "Internal Server Error")
- Sensitive data not in error messages (e.g., "Invalid email" not "Email XYZ not found")
- Test: Trigger 400, 403, 404, 500 errors, verify no PII leakage

**FR2.8** Audit logging (A09:2021 Logging & Monitoring)
- All decisions (score, override, freeze) logged with: timestamp, user_id, officer_id (if override), reason, decision_diff
- All login attempts logged (success/failure, IP, user)
- Test: Create application, score, override → Audit log captures all
- Verify: Audit logs immutable (no updates/deletes post-creation)

**FR2.9** Rate limiting (not implemented in v1)
- Decision: Direct to production without rate limiting (per user request)
- Backlog: Implement in v1.1 if needed
- No API endpoints throttled

**FR2.10** HTTPS in production (A02:2021 Cryptographic Failures)
- All endpoints HTTPS only in production
- HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- Certificate: Valid SSL/TLS (Let's Encrypt or paid)
- Test environment: HTTP acceptable for dev/test

---

### FR3: Load Testing (100+ Concurrent Users)

**FR3.1** Scoring endpoint concurrency test
- Tool: Apache JMeter or Locust
- Concurrent users: 100 users (ramp-up over 1 minute)
- Request: POST /api/scoring/score (typical borrower scoring)
- Expected behavior:
  - Response time: <2 seconds (p95)
  - Error rate: <1%
  - No timeout errors
  - Database handles 100 concurrent transactions
- Test duration: 5 minutes sustained load
- Success: All metrics met, no crashes

**FR3.2** Queue endpoint under load
- Concurrent users: 50 officers (each loading queue of 1000 applications)
- Request: GET /api/applications?status=pending&sort_by=date
- Expected behavior:
  - Response time: <3 seconds (includes sorting/filtering on 1000+ records)
  - Error rate: <1%
- Test duration: 2 minutes sustained load
- Success: Dashboard responsive for all 50 officers

**FR3.3** Database scalability test
- Background: 10,000 applications in database (simulated historical load)
- Concurrent scoring requests: 50 users scoring new applications
- Expected: Query plans optimized, indexes on application_id/status/tier perform well
- Test: Profile queries, verify no full table scans
- Success: No significant slowdown vs 1000-application baseline

**FR3.4** Memory & CPU utilization
- Baseline (1 user): CPU <10%, Memory <500MB
- Peak (100 users): CPU <60%, Memory <2GB (scale assumption: 2GB available)
- Test: Monitor uvicorn process (BE), Node process (FE), no memory leaks
- Success: Process terminates cleanly after load test, memory released

**FR3.5** Frontend load testing
- Tool: Lighthouse, WebPageTest, or synthetic browsers (Selenium)
- Metrics:
  - Page load time: <2 seconds (LCP, FCP)
  - Bundle size: <500KB (gzipped)
  - No JavaScript errors under load
- Test: Simulate 20 concurrent borrowers accessing application form
- Success: No UI freezes, forms responsive

---

### FR4: Production Deployment (Direct Rollout)

**FR4.1** Deployment checklist
- [ ] All environment variables documented (.env.example, .env.prod)
- [ ] Database migration script (if any schema changes from Stage 2)
- [ ] Backend compiled/tested: `pytest tests/ -v` all passing
- [ ] Frontend built: `npm run build`, no warnings, bundle analyzed
- [ ] ML models packaged and version-controlled
- [ ] Docker setup optional (if using containers) or native deployment (direct uvicorn + Node)
- [ ] Database backup strategy (pre-deployment snapshot)
- [ ] Rollback plan (git tag for versioning, previous schema snapshots)

**FR4.2** Deployment target
- Decision: Direct rollout (no canary/phased)
- Assumption: Pre-deployment verification (integration tests, load tests, security audit) validates readiness
- Deployment path: Staging → Production (one-step, monitored)
- Monitoring: Errors logged to console/file, manual monitoring first 2 hours

**FR4.3** Production configuration
- Backend: 
  - `DEBUG=False`
  - `DATABASE_URL=` (production database, TLS connection)
  - `CORS_ORIGINS=https://production-domain.com`
  - `JWT_SECRET_KEY=` (strong random, >32 chars)
  - `ML_MODELS_PATH=/app/models` (mounted or bundled)
- Frontend:
  - `NEXT_PUBLIC_API_URL=https://api.production-domain.com`
  - Build output: Static assets served via CDN or reverse proxy
- SSL/TLS: HTTPS enforced, certificate auto-renewal (if using Let's Encrypt)

**FR4.4** API endpoint availability
- Health check: `GET /api/health` (returns 200 OK)
- All Phase 1-2 endpoints functional (scoring, applications, consent, documents, household, audit, photos, tranches, repayment)
- No stub endpoints left (all wired to engines)

**FR4.5** Data migration (if needed)
- Assumption: No production database exists yet (new deployment)
- If migrating from Stage 2 test database: Data validation script (check row counts, referential integrity)
- Post-deployment: Verify schema matches code (no mismatches)

**FR4.6** Monitoring & alerting (manual for v1)
- Application logs: Check for errors hourly
- Database health: Verify connections active, query performance
- User feedback: Monitor for UX issues (no dashboard loading, scoring failures)
- Success metric: 0 critical errors in first 2 hours post-deployment

---

## Non-Functional Requirements

### NFR1: Performance
- Scoring API response time: <2 seconds (p95)
- Queue page load: <3 seconds
- Frontend bundle size: <500KB gzipped
- Database query time: <100ms (p95) for common queries (applications list, decision lookup)

### NFR2: Reliability
- Backend uptime: 99% (SLA for v1, assume 0 maintenance windows in first week)
- Database: Single instance (no replication, backup via snapshots)
- No data loss on restart
- Graceful degradation: If adapters fail (UPI, GST), scoring falls back to available data

### NFR3: Scalability
- Support 100+ concurrent users without service degradation
- Database supports 10,000+ applications without query slowdown
- Frontend CDN-ready (static assets cacheable)

### NFR4: Maintainability
- Code documented (docstrings on all engines)
- API documented (OpenAPI/Swagger at /docs)
- Test coverage >80% on core engines
- All Phase 1-2 engines testable offline (deterministic adapters)

### NFR5: Security
- All OWASP Top 10 items addressed (see FR2)
- Data encryption at rest (database): TBD per deployment environment
- Data encryption in transit: HTTPS + TLS 1.2+
- Secrets management: Environment variables, no hardcoded credentials

### NFR6: Auditability
- All decisions logged with reason + timestamp
- All overrides logged with officer_id + reason
- Audit trail immutable (no deletes post-creation, only admin can view)
- Compliance-ready for regulatory review (decision reproducibility, no bias by gender/caste)

---

## Acceptance Criteria

### AC1: All Integration Tests Passing
1. **Borrower workflow end-to-end**: Application created, consent granted, photos uploaded (3 shots valid), documents uploaded, household data entered, scoring executed (all 9 Phase 1 engines invoked in order), result page displays tier/amount/rate/EMI/reasons/tranche plan → Status: PASS ✓ / FAIL ✗
2. **Officer dashboard workflow**: Queue view loads 10+ applications with filters working (by tier, frozen status), case view shows 5 tabs correctly, replay modifies inputs and rescores (decision not persisted), override with reason recorded in audit trail → Status: PASS ✓ / FAIL ✗
3. **Tier-driven verification**: Tier 1 with 5.99 months verified data rejected, Tier 1 with 6.0 months verified data accepted, Tier 2 with 11.99 months rejected, Tier 2 with 12.0 months accepted, Tier 3 with 23.99 months rejected → Status: PASS ✓ / FAIL ✗
4. **Tranche gates**: Tranche 1 released on approval, Tranche 2 release blocked until Tranche 1 EMI marked on-time, Tranche 2 released after → Status: PASS ✓ / FAIL ✗
5. **Stop rule freeze**: 2 missed EMIs recorded, application frozen, frozen status visible in queue, further tranches cannot be requested → Status: PASS ✓ / FAIL ✗
6. **Photo verification**: Valid photo (code + location) accepted, photo without code rejected, photo >500m from rent address rejected → Status: PASS ✓ / FAIL ✗
7. **Plain language reasons**: At least 4 reasons displayed to borrower in plain English (no code names, glossary links work for 18 terms) → Status: PASS ✓ / FAIL ✗
8. **ML reproducibility**: 100 synthetic shops scored in backend, decisions exported and rescored in ML pipeline, outputs match 100% (rule-based determinism) → Status: PASS ✓ / FAIL ✗

### AC2: Security Audit Complete
1. **JWT authentication**: All endpoints (except /health, /login) reject requests without valid token, token expiry enforced, refresh token rotation working → Status: PASS ✓ / FAIL ✗
2. **Data isolation**: Borrower A queries Borrower B's application → 403 Forbidden, officer attempts override without approver role → 403 Forbidden → Status: PASS ✓ / FAIL ✗
3. **SQL injection prevention**: SQL payloads in application_id, shop_id parameters handled safely (no database errors, queries execute correctly with literal values) → Status: PASS ✓ / FAIL ✗
4. **XSS prevention**: HTML/script tags in reason text or document file names rendered safely (no script execution) → Status: PASS ✓ / FAIL ✗
5. **Sensitive data protection**: Passwords stored as bcrypt hashes, SSN/Aadhaar masked in logs (**** format), no plaintext tokens in responses → Status: PASS ✓ / FAIL ✗
6. **CORS validation**: Cross-origin requests from unauthorized domains rejected (OPTIONS 403), allowed domain (production-domain.com) accepted → Status: PASS ✓ / FAIL ✗
7. **File upload validation**: EXE/ZIP uploaded with PDF extension rejected, JPG/PNG/PDF accepted, file size >10MB rejected → Status: PASS ✓ / FAIL ✗
8. **Error handling**: 500 errors return generic message (no stack trace), 403 errors don't expose reasons ("Insufficient permissions" not "User role is 'borrower' not 'approver'") → Status: PASS ✓ / FAIL ✗
9. **Audit logging**: Every decision/override logged to AuditLog table with timestamp, user_id, officer_id, reason, decision_diff; logs immutable → Status: PASS ✓ / FAIL ✗
10. **Rate limiting**: NOT IMPLEMENTED (backlog for v1.1); note in deployment docs → Status: BACKLOG → DEPLOYED ✓

### AC3: Load Test 100+ Concurrent Users
1. **Scoring endpoint under load (100 concurrent users, 5 min duration)**: Response time <2s (p95), error rate <1%, zero crashes → Status: PASS ✓ / FAIL ✗
2. **Queue endpoint under load (50 officers, 1000+ applications each, 2 min duration)**: Response time <3s (p95), error rate <1%, no timeouts → Status: PASS ✓ / FAIL ✗
3. **Database concurrency**: No connection pool exhaustion, queries complete successfully under load, no deadlocks observed → Status: PASS ✓ / FAIL ✗
4. **Memory/CPU usage**: Peak CPU <60%, peak memory <2GB (on assumed 2GB available), no memory leaks (process releases memory post-load) → Status: PASS ✓ / FAIL ✗
5. **Frontend load test**: Page load time <2s under 20 concurrent users, bundle size <500KB, no JS errors → Status: PASS ✓ / FAIL ✗

### AC4: Production Deployed & Verified Live
1. **Deployment successful**: Backend running on production domain, health check (`GET /api/health`) returns 200, frontend loads on production URL → Status: PASS ✓ / FAIL ✗
2. **All endpoints functional**: Scoring works end-to-end (application creation to result display), queue accessible, override workflow functional → Status: PASS ✓ / FAIL ✗
3. **Database verified**: Schema matches code, all tables created, no migration errors, data consistent → Status: PASS ✓ / FAIL ✗
4. **Monitoring active**: Logs accessible, error tracking enabled, no critical errors in first 2 hours post-deployment → Status: PASS ✓ / FAIL ✗
5. **Documentation updated**: Deployment guide written, API docs live (/docs endpoint), environment variables documented in .env.example → Status: PASS ✓ / FAIL ✗

---

## Out of Scope

### O1: Real-World Data Integration
- Mock OCR only (not real image processing via AWS Rekognition, Google Vision, or Tesseract)
- Deterministic adapters for UPI, GST, Account Aggregator (not real APIs)
- Synthetic test data only, no production merchant data
- **Reason:** Requires external API credentials, rate limits, compliance (PII regulations). Mocks support full offline testing.

### O2: ML Model Training
- Tier assignment and tranche planning use rule-based logic (not ML)
- ML pipeline provides evaluation/simulation (not live scoring)
- No logistic regression scorecard, no repayment capacity model training
- **Reason:** Rule-based system is more explainable and defensible for lending decisions. ML models deferred to Phase 3.

### O3: Advanced Features (Phase 3+)
- Regional language support (Hindi, Kannada, Tamil)
- Advanced dashboards (cohort analysis, lending trends)
- Mobile app (web-only for v1)
- SMS/email notifications
- Supplier confirmation workflow
- PDF export
- Monte Carlo scenario simulation
- **Reason:** Beyond Phase 1-2 scope, require additional development.

### O4: Infrastructure as Code
- No Docker containerization, Kubernetes orchestration, Terraform IaC
- Manual deployment (or simple bash scripts) to production server
- Single-machine deployment (no microservices, no auto-scaling)
- **Reason:** v1 focuses on feature completeness. Infrastructure code deferred to v1.1 if scaling required.

### O5: Real Rate Environment Data
- No integration with MSME lending rate databases (SEBRI, Credy, etc.)
- Rates hardcoded per tier in `RateEnvironment` table or policy config
- No market rate fetching or dynamic rate adjustments
- **Reason:** Requires data partnerships. Hardcoded rates sufficient for v1 demo/MVP.

### O6: Fair Lending Audits
- No bias testing (protected attributes: gender, caste, religion, age)
- No fairness metrics (approval rate parity, disparate impact ratio)
- No remediation workflows if bias detected
- **Reason:** Evaluation framework exists in ML but not operationalized in live system. Can add post-launch if regulatory requirement emerges.

### O7: Repayment Tracking UI
- No borrower app to upload EMI payment proof (bank transfer screenshot, UPI confirmation)
- Officer records EMI manually via dashboard
- No automatic EMI debit/collection
- **Reason:** Phase 1 focuses on decisioning, not full repayment automation. EMI tracking via officer dashboard is sufficient for MVP.

### O8: Rate Limiting
- No per-user/per-IP API rate limiting (decision: direct to production without throttling)
- No queue-based async job processing
- All requests processed synchronously
- **Reason:** User request. Can add in v1.1 if DDoS/abuse issues arise.

---

## Assumptions

### A1: Environment & Infrastructure
- Production environment has: 2GB RAM, 2 CPU cores (minimum), 20GB disk for database + logs
- Frontend and backend can run on same machine or separate machines (if separate, low-latency network assumed)
- Database: SQLite for v1 (can upgrade to PostgreSQL in v1.1 if needed)
- SSL certificate available (Let's Encrypt or self-signed for testing)

### A2: Team & Skills
- Backend team: 1 engineer (maintains FastAPI code, runs tests, deploys)
- Frontend team: 1 engineer (React/TypeScript, builds, deploys static assets)
- ML team: 1 engineer (maintains generator, evaluation scripts, updates tier rules if needed)
- DevOps/SRE: Not required for v1 (manual deployment, no CI/CD pipeline)

### A3: Data & Testing
- 100 synthetic shops sufficient for load testing (representative portfolio by tier)
- Deterministic adapters reproduce exact same data for same shop_id (enables testing)
- No real borrower PII used (all synthetic/test data)
- Integration tests can run offline (no external API calls)

### A4: Regulatory & Compliance
- No regulatory approval required before launch (MVP phase)
- No RBI compliance enforcement (if applicable) until Phase 3
- No GST compliance (system generates no tax liabilities)
- Consent framework: borrower must accept consent text before scoring (UI enforces)

### A5: Product Decisions
- Tier assignment is rule-based (not ML), deterministic
- Tranche gates are rule-based (not discretionary)
- Stop rule is deterministic (freeze on 2 missed EMIs, no exceptions)
- No manual overrides of tier or stop rule (only override of final loan amount by approver role)

---

## Success Metrics

### SM1: Testing
- All 8 integration tests (AC1) pass → PASS = 100%, FAIL = 0 tests failing
- Security audit (AC2) finds 0 critical issues (medium/low issues may be deferred to v1.1)
- Load test (AC3) meets all targets (response time, error rate, resource usage)

### SM2: Deployment
- Time to production: <4 hours (from approval to live verification)
- Deployment errors: 0 critical errors (retries/rollbacks not required)
- Downtime: 0 minutes (direct rollout assumed stable)

### SM3: Live Operations
- First 2 hours post-deployment: 0 critical errors in logs
- Scoring success rate: 95%+ (5% expected for invalid inputs/edge cases)
- Officer dashboard: All 5 tabs load correctly for 100% of cases viewed

### SM4: Business Impact
- Time to decision: Borrower completes application in <15 minutes (frontend usability)
- Officer review time: <5 minutes per case (dashboard efficiency)
- Approval rate: Expected 40-60% (rule-based tier assignment, representative portfolio)

---

## Dependencies & Risks

### D1: Frontend Tier-Verified Months Dependency
- Requirement: "tier drives verified_months" — verified months must determine tier, not vice versa
- Deliverable: Frontend must collect data sources (AA, GST, UPI months), backend calculates tier based on data overlap
- Risk: If frontend doesn't capture month ranges correctly, tier assignment fails
- Mitigation: Frontend validation (warn if <6 months data), backend validation (reject tier if data insufficient)

### D2: All Phase 1 Engines Must Be Wired
- Dependency: 9 Phase 1 engines (photo verification, source agreement, verified window, GST coverage, tier assignment, amount rule, rate calculation, tranche plan, tranche rule, stop rule) must all be orchestrated in scoring endpoint
- Risk: If any engine skipped/mocked, scoring incomplete
- Mitigation: Integration test validates all engines invoked and their outputs appear in decision

### D3: Database Schema Finalized
- Dependency: Decision model schema must match Phase 1 outputs (tier, verified_months, source_agreement_score, tranche_plan_json, etc.)
- Risk: If schema mismatches code, tests fail, endpoints return wrong data
- Mitigation: Schema review before implementation, migration script prepared

### D4: Backend Determinism
- Dependency: Same inputs (shop_id, household data, consent date) must produce identical decisions on repeated runs
- Risk: If stochastic elements exist (random number generation, external API variability), ML evaluation fails
- Mitigation: Audit all engines for non-determinism, mock all external adapters, run reproducibility test

### D5: Load Test Environment
- Dependency: Load testing requires production-like environment (database size 10,000+ records, network latency similar to prod)
- Risk: If testing on minimal data/fast network, load test results unreliable
- Mitigation: Synthetic data generator scales to 10,000 shops, network simulation available

### D6: Security Scan Tooling
- Dependency: OWASP Top 10 validation can use automated tools (OWASP ZAP, Burp Suite Community) or manual testing
- Risk: Manual testing incomplete (missed vulnerabilities)
- Mitigation: Use free tools (OWASP ZAP) for automated scanning, supplement with manual spot checks

### D7: Production Environment Access
- Dependency: Deployment requires server/cloud account access (AWS, DigitalOcean, on-premises)
- Risk: If no environment available, cannot deploy
- Mitigation: Assume environment pre-provisioned, credentials shared with team

---

## Timeline & Effort Estimate

| Phase | Task | Duration | Owner | Deliverable |
|-------|------|----------|-------|-------------|
| **A** | Backend integration wiring | 1.5 days | BE team | All endpoints wired to Phase 1 engines, tests passing |
| **A** | Frontend-backend integration testing | 1 day | FE team | 8 integration tests passing, screenshots/logs |
| **A** | ML reproducibility validation | 0.5 days | ML team | 100 shops scored, outputs match (determinism verified) |
| **B** | Load testing (setup + execution) | 1 day | QA/BE team | Load test report (metrics, graphs, analysis) |
| **C** | Security audit (manual + tooling) | 1 day | Security/BE team | Security audit report (10 OWASP items checked, findings documented) |
| **D** | Deployment preparation | 0.5 days | DevOps/BE team | .env.example, migration script, deployment guide, rollback plan |
| **E** | Production deployment + verification | 0.5 days | BE team | Health check passing, endpoints functional, logs clean for 2 hours |
| **Total** | | **6 days** | **All teams** | **Live in production with all criteria met** |

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Phase 1 engines have bugs | Medium | High | Run full test suite (286 tests), fix failures before integration testing |
| Frontend-backend API contract mismatch | Low | High | Review API schemas (Pydantic models) before implementation, integration tests validate contract |
| Load test reveals performance bottleneck | Medium | Medium | Profile slow queries pre-deployment, add indexes if needed, scale hardware if required |
| Security audit finds critical vulnerability | Low | Critical | Perform security review before deployment, use automated scanner (OWASP ZAP), fix critical issues before go-live |
| Production database unavailable at launch | Low | Critical | Database backup strategy, restore procedure tested, pre-deployment snapshot taken |
| Rollback needed post-deployment | Low | Medium | Git tag for each release, previous database schema/data backed up, rollback procedure documented |
| Real OCR/APIs become critical later | Low | Medium | Documented that mocks used in v1, plan to integrate real services in Phase 3 |

---

## Glossary

- **AC:** Acceptance Criteria
- **API:** Application Programming Interface
- **BE:** Backend (Python/FastAPI)
- **FE:** Frontend (React/TypeScript)
- **JWT:** JSON Web Token
- **ML:** Machine Learning
- **OWASP:** Open Web Application Security Project
- **Phase 1:** Tier 1-3 assignment, photo + source agreement verification, deterministic amounts + rates + tranche plans
- **Phase 2:** Overlay Phase 1 with repayment tracking, EMI schedules, stop rules, override workflows
- **Phase 3:** Real ML models, advanced dashboards, mobile app, regional languages
- **SLA:** Service Level Agreement
- **SM:** Success Metric
- **TLS:** Transport Layer Security

---

## Sign-Off

**Document Status:** APPROVED FOR IMPLEMENTATION  
**Prepared by:** Requirements & Design Agent  
**Date:** 2026-11-21  
**Next Step:** Design Phase (wiring details, engine orchestration, security implementation specifics)
