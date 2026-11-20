# UdyamCred: Build Plan

Stages: **I** = Initial, **M** = MVP, **F** = Final. Every feature from the scope is included. Items moved from the cut list are placed in Final.

---

## Part 1: Stages

### Stage 1: Initial (foundation and core check)

**Checkpoint:** For a synthetic shop, the system shows whether its sales match its stock, and the verdict is visible on a simple page. Two shops with the same UPI inflow get different verdicts.

- **Frontend:** Layout and a basic borrower form (amount, purpose). Placeholder result page.
- **Backend:** Project setup, database schema v1 (shops, transactions, purchases, stock, applications, decisions, overrides), GSTIN validator, stock reconciliation function, one API endpoint that returns the verification result.
- **ML and data:** Synthetic data generator v1 with hidden shop health. Reconciliation features. UPI-only baseline model for comparison.
- **Other:** Repo, environment setup, seed scripts, basic tests for GSTIN and reconciliation, policy config file (caps, rate bands, EMI share), consent text draft.

*Cut list:* OCR, graph view, borrower app extras.

### Stage 2: MVP (working end to end)

**Checkpoint:** A borrower applies, adds documents, and gets a decision with amount, rate, EMI schedule and reasons. A bank officer sees the decision, changes an input in the replay view, and overrides with a reason. The override is recorded. Results are measured against the baseline.

- **Frontend:** Borrower flow (application, consent, documents or manual entry, household budget, result with reasons). Bank queue, decision screen, replay, override form, audit view of decisions and overrides.
- **Backend:** APIs for applications, documents, household budget, scoring, loan rules, overrides and audit records. ABCA v1 (two sources). Vintage engine. Round-trip detection v1. Consent storage. Basic roles (officer, approver, auditor). Mock adapters for UPI, Account Aggregator and GST registry.
- **ML and data:** Scorecard (logistic regression) with risk bands, confidence and reason codes. Second synthetic generator for testing. Evaluation script for the first two claims (approval rate vs baseline, round-trip detection). Fixed fund-split rules.
- **Other:** Staging deployment. Tests for each engine. Data dictionary and short README.

*Feature freeze at the end of this stage.*

*Cut list:* Fund plan scenarios, fairness chart, PDF export.

### Stage 3: Final (polished and evaluated)

**Checkpoint:** Every claim in the doc has a measured result. Fund plan and three-scenario projection are shown. Fairness audit runs with and without family size. The demo runs start to finish without manual fixes.

- **Frontend:** Fund plan and scenario table, fairness chart, supplier confirmation page, report export view, layout and copy polish.
- **Backend:** Profit and loss scenarios, fund allocation service, supplier confirmation workflow, fairness audit job, PDF or CSV export, error handling, logging of which rate date was used.
- **ML and data:** Scorecard calibration check. Reason stability test. Fairness audit results. Model card. Stress scenario checks.
- **Other:** End-to-end tests, privacy check (no real personal data stored, consent respected), final deployment, demo script, final documentation.

---

## Part 2: Features by category

### Frontend (React / Next.js)

- Landing page and layout **[I]**
- Owner and officer login screens **[I]**
- Application form (amount, purpose) **[I]**
- Consent screen **[I]**
- Shared components, loading and error states **[I]**
- Document upload and status page **[M]**
- Manual purchase bill entry form **[M]**
- Household budget form **[M]**
- Borrower result screen (decision, reasons, how to improve) **[M]**
- Bank application queue and detail view **[M]**
- Bank decision screen (score, band, confidence, amount, rate, schedule) **[M]**
- Replay view (change inputs, see result move) **[M]**
- Override form with required reason **[M]**
- Audit view of decisions and overrides **[M]**
- Mobile-friendly layout **[M]**
- Fund plan view for borrower **[F]**
- Three-scenario profit and loss table **[F]**
- Supplier confirmation page **[F]**
- Fairness chart page **[F]**
- Round-trip transaction graph view **[F]**
- Report export screen **[F]**
- Explanation text in Kannada and Hindi (if time allows) **[F]**

### Backend (Python, FastAPI)

- Project setup, config and environment variables **[I]**
- Database schema v1 **[I]**
- Input validation and error handling **[I]**
- Logging **[I]**
- Policy config store (caps, rate bands, EMI share) **[I]**
- GSTIN format and checksum validator **[I]**
- Stock reconciliation function **[I]**
- Verification API **[I]**
- Mock adapters for UPI, Account Aggregator, GST registry (interfaces) **[I]**
- Application APIs **[I]**
- Consent storage and withdrawal **[M]**
- Document upload service and secure storage **[M]**
- Login and roles (officer, approver, auditor) **[M]**
- ABCA estimator with two sources **[M]**
- Vintage engine (earliest date from two sources) **[M]**
- Cross-checks: ledger, electricity, rent **[M]**
- Round-trip detection, simple version **[M]**
- Household surplus and EMI cap **[M]**
- Loan rule engine (amount, rate, tenor) **[M]**
- Rate band store, with the date each rate was taken **[M]**
- Scoring endpoint **[M]**
- Replay engine (does not change the saved decision) **[M]**
- Override workflow (reason required, stored with the decision) **[M]**
- Audit record APIs **[M]**
- Fund allocation split rules **[M]**
- Co-borrower data handling **[M]**
- ABCA with three sources **[F]**
- Full round-trip graph analysis **[F]**
- Scenario profit and loss engine **[F]**
- Supplier confirmation workflow **[F]**
- Fairness audit job **[F]**
- Background job runner **[F]**
- PDF and CSV export **[F]**
- Bill OCR and field extraction **[F]**

### ML and data

- Synthetic data generator v1 (hidden shop health) **[I]**
- Feature builder with missing-data handling **[I]**
- Reconciliation features **[I]**
- UPI-only baseline model **[I]**
- Scorecard (logistic regression), main model **[M]**
- Risk bands **[M]**
- Confidence calculation (from source agreement) **[M]**
- Reason codes from model weights, with template text **[M]**
- Bureau-only baseline **[M]**
- Second synthetic generator (train and test separation) **[M]**
- Evaluation script for claims 1 and 2 **[M]**
- Scorecard calibration check **[F]**
- Reason stability test **[F]**
- Fairness audit, with and without family size **[F]**
- Evaluation script for claims 3 to 5 **[F]**
- Stress scenario sensitivity analysis **[F]**
- Round-trip anomaly model (Isolation Forest, optional) **[F]**
- Model card and data card **[F]**
- LLM wording for reasons (templates stay as fallback) **[F]**

### Infrastructure, testing and documentation

- Repo, branch rules, basic CI **[I]**
- Unit tests for GSTIN, reconciliation, EMI, audit records **[I]**
- Data dictionary and README **[I]**
- Staging deployment **[M]**
- Security basics: file type checks, secrets handling, input sanitising **[M]**
- API documentation **[M]**
- Tests for every engine, including scorecard sign checks (more debt or fewer verified records must never raise the score) **[M]**
- Production-style deployment **[F]**
- End-to-end tests **[F]**
- Privacy and consent check **[F]**
- Final documentation pass **[F]**

---

## Part 3: What is a model, a rule, or an AI step

### Trained ML models

| Model | Type | Purpose | Stage |
|---|---|---|---|
| UPI-only baseline | Logistic regression | Comparison for claim 2 | I |
| Credibility scorecard | Logistic regression | Main credit score, explainable | M |
| Round-trip anomaly model (optional) | Isolation Forest | Unusual counterparty patterns | F |

### Rules and formulas (not trained)

| Item | Type | Purpose | Stage |
|---|---|---|---|
| Stock reconciliation | Rule | Sales vs stock plus margin | I |
| GSTIN validator | Rule (checksum) | Validate supplier GSTIN format | I |
| Bureau-only baseline | Rule | Comparison for claim 1 | M |
| Round-trip detection (simple) | Graph rules | Flag circular money | M |
| Confidence | Rule | Based on how much sources agree | M |
| Risk bands | Rule | Map score to Low, Moderate, High, Needs Review | M |
| Loan amount | Rule | Lowest of repayment, stock and policy limits | M |
| Rate (ROI) | Rule | Starting band from published MSME rates, set by risk band | M |
| EMI cap | Rule | Fixed share of household-adjusted surplus | M |
| Fund split | Rule | Fixed split across stock, buffer, expansion, reserve | M |
| Three-scenario projection | Formula | Base, optimistic, stress profit and coverage | F |
| Vintage | Rule | Earliest date supported by two sources | M |

### AI steps (LLM, not part of scoring)

| Step | Type | Purpose | Stage |
|---|---|---|---|
| Bill field extraction | OCR plus LLM, with rule checks | Read purchase bills | F |
| Reason wording | LLM, with template fallback | Plain-language reasons | F |

**Count:** 2 trained models in Initial and MVP (UPI baseline and scorecard). 1 optional in Final (Isolation Forest). About 12 rules and formulas. 2 AI steps, both in Final and both optional.

---

## Part 4: Agentic structure

**Decision: no multi-agent design.** Use a fixed pipeline.

- Judges and bank auditors need the same input to give the same decision.
- A fixed pipeline is easier to test, explain and defend.
- Agent coordination adds work with no gain for this problem.

If judges ask for an agentic design, present the two AI steps above as agent steps inside the fixed pipeline.

---

## Part 5: Risk

Final carries many features plus the evaluation work. If the team runs short, watch two places: Bill OCR and the fairness audit. Every claim in the doc depends on evaluation results, so keep the evaluation script in Final even if features are trimmed.