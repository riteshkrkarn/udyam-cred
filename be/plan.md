# UdyamCred Stage 1 Backend — Implementation Plan

Stage 1 delivers the foundation for UdyamCred: a FastAPI backend that, for a
synthetic shop, decides whether its declared sales match its stock given a
category margin, and shows the verdict. The headline Stage-1 claim — *two shops
with the same UPI inflow get different verdicts* — is enforced and tested.

## Layout

```
be/
  app/
    __init__.py
    config.py          # settings from env/.env (lru_cache singleton)
    database.py        # SQLAlchemy engine, SessionLocal, Base, init_db, get_db
    models.py          # ORM: User, Shop, ReconciliationResult, RefreshToken
    utils.py           # utcnow_naive() helper (naive UTC for SQLite storage)
    policy.py          # Policy / CategoryPolicy loader for config/policy.yaml
    gstin.py           # GSTIN validator (length, state code, checksum)
    reconciliation.py  # reconcile() + reconcile_many()
    auth.py            # bcrypt hashing, JWT access tokens, refresh hashing/expiry
    schemas.py         # pydantic request/response models
  synth/
    generator.py       # SyntheticDataGenerator (deterministic, scenario-based)
  config/
    policy.yaml        # 8 leaf shop categories + kirana_overall aggregate, margins
  scripts/
    seed.py            # init_db_tables, create_test_users, load_synthetic_data, CLI
  tests/
    conftest.py        # shared fixtures (policy, generator, engine, db_session, client)
    test_gstin.py
    test_generator.py
    test_reconciliation.py
    test_seed.py
    test_golden.py
    test_auth.py
    golden_expected.csv
  data/synthetic/      # generated shop CSVs land here (gitignored)
  requirements.txt
  .env.example
  .gitignore
  pytest.ini
  main.py              # FastAPI app: health, auth, /reconcile
  plan.md
```

## Domain model and reconciliation

A shop carries: `gstin`, `shop_category` (one of 8 leaf categories),
`purchases` (cost of goods sold), `gst_turnover` (declared sales), and
`upi_turnover` (digital receipts).

The spec's inverse formula (margin on selling price) is implemented exactly:

```
expected_sales = goods_sold / (1 + margin)
```

For a category margin range `[margin_low, margin_high]` the expected-sales band
is:

```
expected_sales_high = goods_sold / (1 + margin_low)   # lower margin -> higher expected
expected_sales_low  = goods_sold / (1 + margin_high)  # higher margin -> lower expected
```

A tolerance (`policy.tolerance`, default ±0.5%) is applied to both ends so
point-valued categories (e.g. `kirana_with_inventory = 15%`) behave as a thin
band rather than a degenerate point.

`reconcile(shop, policy)` returns a verdict:

| verdict   | when                                                                 |
|-----------|----------------------------------------------------------------------|
| rejected  | GSTIN fails format/state/checksum validation                         |
| flagged   | UPI receipts exceed declared GST sales, or declared sales fall outside the expected band (suppression if below, overstatement if above) |
| approved  | declared sales sit inside the expected margin band                   |

## GSTIN validation

15-char structure: state code (01–38) + 5 letters + 4 digits + 1 letter + 1
alphanumeric entity code + `Z` + 1 alphanumeric check digit.

Checksum: map each of the first 14 chars to 0–35 (0-9 → 0-9, A-Z → 10-35), apply
alternating weights 1,2,1,2,… starting at 1, add `(product // 36) + (product % 36)`
per char, then `check = (36 - sum % 36) % 36`. `is_valid_gstin` never raises;
`validate_gstin` raises `GSTINError`. `make_valid_gstin(prefix14)` appends the
correct check digit (used by tests and the generator).

## Policy (config/policy.yaml)

Eight leaf shop categories under `shop_categories`, plus `kirana_overall`
(8–10%) under `aggregates` as the parent reference band. The 10 listed margin
figures map to 8 leaf categories because `kirana_overall` is the aggregate.

| category                  | margin      |
|---------------------------|-------------|
| kirana_with_inventory     | 15%         |
| kirana_without_inventory  | 10%         |
| branded_staples           | 3–9%        |
| packaged_fmcg             | 7–14%       |
| beverages_impulse         | 10–18%      |
| personal_care             | 12–20%      |
| general_merchandise       | 14–25%      |
| loose_goods               | 14–30%      |

## Synthetic generator

`SyntheticDataGenerator(policy, seed)` is fully deterministic for a given seed
(seeded `random.Random`). Each shop's *verdict is fixed by construction*: the
relationship between `purchases`, `gst_turnover` and `upi_turnover` is chosen
per scenario, so verdicts are meaningful rather than accidental. A small seeded
jitter on `purchases`/`inventory` provides variety without changing verdicts.

Scenarios repeat every 10 shops. The first ten (seed 42) are the golden set:

| shop | scenario            | category                 | verdict  |
|------|---------------------|--------------------------|----------|
| 0    | approved            | kirana_without_inventory | approved |
| 1    | suppression        | loose_goods              | flagged  |
| 2    | invalid_gstin      | packaged_fmcg            | rejected |
| 3    | approved           | branded_staples          | approved |
| 4    | upi_exceeds_gst    | beverages_impulse        | flagged  |
| 5    | approved           | personal_care            | approved |
| 6    | suppression         | general_merchandise      | flagged  |
| 7    | approved           | packaged_fmcg            | approved |
| 8    | suppression         | kirana_with_inventory    | flagged  |
| 9    | approved           | loose_goods              | approved |

Verdict mix: 5 approved, 4 flagged, 1 rejected.

**Pair case.** Shops 0 and 1 are explicitly given the same UPI inflow
(400,000). Shop 0's declared sales sit at its expected band midpoint (margin
10%, purchases ≈1.0m → expected ≈0.91m) so it is approved. Shop 1 has higher
purchases and a higher-margin category (loose_goods, 14–30%) so its expected
band is well above its declared sales → flagged. Same UPI, different verdicts,
because the verdict depends on the stock/margin reconciliation, not UPI alone.

## Auth (JWT, refresh rotation, remember-me)

- **Access token:** signed JWT (HS256), 15-minute lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **Refresh token:** opaque `secrets.token_urlsafe`, stored **hashed** (sha256)
  in `refresh_tokens`. Rotation on `POST /auth/refresh` revokes the old token
  (`revoked=True`, `replaced_by` set) and issues a new one — single-use.
- **Remember me:** refresh lifetime is 1 day with `remember_me=true`, else 1 hour
  (`REMEMBER_ME_EXPIRE_HOURS` / `REFRESH_TOKEN_EXPIRE_HOURS`).
- Passwords hashed with bcrypt; the raw value is never stored.

Endpoints: `GET /health`, `POST /auth/register`, `POST /auth/login`,
`POST /auth/refresh`, `POST /auth/logout`, `POST /reconcile` (auth-protected),
`GET /shops/me`.

## Running

```bash
# from be/
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# set up database, test users, and 10 synthetic shops (seed 42)
python scripts/seed.py                     # also: --shops N --seed S --csv path.csv
python scripts/seed.py --init-only          # tables only

# serve
uvicorn main:app --reload

# tests with coverage
python -m pytest tests --cov=app --cov=synth --cov=scripts --cov=main --cov-report=term-missing
```

## Test results

95 tests pass, 90% coverage. Suites:

- `test_gstin.py` — valid GSTINs (7), invalid cases (wrong length, bad state,
  bad pattern, bad checksum), checksum internals.
- `test_generator.py` — determinism (same seed equal, different seed different),
  shape, the pair case, scenario/verdict composition.
- `test_reconciliation.py` — approved/rejected/flagged branches, inverse-formula
  math, band ordering, ORM-object input, unknown-category error.
- `test_seed.py` — init_db tables, idempotent users, load_synthetic_data counts,
  verdict mix, replacement on reload, pair case in DB, CSV export.
- `test_golden.py` — seed-42 dataset reproduces `golden_expected.csv` (shop_id,
  category, gstin_valid, verdict) and the pair case.
- `test_auth.py` — register/login, protected `/reconcile`, refresh rotation
  (old token revoked, single-use), logout.

## Notes and assumptions

- The spec's formula `expected_sales = goods_sold / (1 + margin)` is implemented
  literally. With a positive margin this makes `expected_sales < goods_sold`;
  the dataset and verdicts are self-consistent with that formula. `goods_sold`
  is the shop's purchases (cost of goods); `expected_sales` is the declared
  sales band implied by the category margin.
- `kirana_overall` is modelled as an aggregate, not a leaf shop category, so the
  "8 shop categories" and the 9 listed margin figures are consistent.
- Test DBs use in-memory SQLite (`StaticPool`, single connection) so API writes
  are visible to direct queries in the same test.
- `data/synthetic/*.csv` is gitignored (generated); `tests/golden_expected.csv`
  is the committed regression lock.
