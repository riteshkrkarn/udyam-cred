"""Seed script: create tables, test users, and load synthetic shops + reconcile.

Usage:
    python scripts/seed.py                # init_db + users + 10 shops (seed 42)
    python scripts/seed.py --shops 50 --seed 7
    python scripts/seed.py --init-only
    python scripts/seed.py --csv data/synthetic/shops.csv

The functions (init_db, create_test_users, load_synthetic_data) are importable
so tests can exercise them against an injected session.
"""
from __future__ import annotations

import argparse
import os
import sys

# Make the package importable when run as a script from the be/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.models import ReconciliationResult, Shop, User  # noqa: E402
from app.policy import load_policy  # noqa: E402
from app.reconciliation import reconcile  # noqa: E402
from synth.generator import SyntheticDataGenerator  # noqa: E402

DEFAULT_TEST_USERS = [
    ("borrower@udyamcred.test", "borrower", "borrowerpass"),
    ("officer@udyamcred.test", "officer", "officerpass"),
    ("approver@udyamcred.test", "approver", "approverpass"),
    ("auditor@udyamcred.test", "auditor", "auditorpass"),
]


def init_db_tables(engine_=None) -> None:
    """Create all tables on the given engine (defaults to the configured engine)."""
    from app import models  # noqa: F401  (registers tables on metadata)

    Base.metadata.create_all(bind=engine_ if engine_ is not None else engine)


def create_test_users(db: Session, users=None) -> list[User]:
    """Idempotently create test users. Returns the User objects."""
    users = users or DEFAULT_TEST_USERS
    created = []
    for email, role, password in users:
        existing = db.query(User).filter_by(email=email).first()
        if existing is not None:
            created.append(existing)
            continue
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
        created.append(user)
    db.commit()
    return created


def load_synthetic_data(
    db: Session,
    n: int = 10,
    seed: int = 42,
    policy=None,
    write_csv: str | None = None,
) -> tuple[list[Shop], list[ReconciliationResult]]:
    """Generate n shops, persist them, reconcile each, and store the results.

    Existing shops with the same shop_id are replaced.
    """
    policy = policy or load_policy()
    gen = SyntheticDataGenerator(policy, seed=seed)
    shops_data = gen.generate(n, seed=seed)

    if write_csv:
        gen.generate_csv(write_csv, n_shops=n, seed=seed)

    shops_out: list[Shop] = []
    results_out: list[ReconciliationResult] = []

    for s in shops_data:
        existing = db.query(Shop).filter_by(shop_id=s["shop_id"]).first()
        if existing is not None:
            db.delete(existing)
            db.flush()
        shop = Shop(
            shop_id=s["shop_id"],
            gstin=s["gstin"],
            shop_name=s["shop_name"],
            shop_category=s["shop_category"],
            state_code=s["state_code"],
            gstin_valid=s["gstin_valid"],
            upi_turnover=s["upi_turnover"],
            gst_turnover=s["gst_turnover"],
            purchases=s["purchases"],
            inventory_value=s["inventory_value"],
            cash_sales=s["cash_sales"],
        )
        db.add(shop)
        db.flush()

        result = reconcile(s, policy)
        rr = ReconciliationResult(
            shop_id=shop.id,
            verdict=result["verdict"],
            margin_low=result["margin_low"],
            margin_high=result["margin_high"],
            goods_sold=result["goods_sold"],
            expected_sales_low=result["expected_sales_low"],
            expected_sales_high=result["expected_sales_high"],
            reported_sales=result["reported_sales"],
            upi_turnover=result["upi_turnover"],
            gst_turnover=result["gst_turnover"],
            gstin_valid=result["gstin_valid"],
            reason=result["reason"],
        )
        db.add(rr)
        db.flush()
        shops_out.append(shop)
        results_out.append(rr)

    db.commit()
    return shops_out, results_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the UdyamCred database.")
    parser.add_argument("--shops", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--csv", type=str, default=None, help="also write shops CSV here")
    args = parser.parse_args()

    init_db_tables()
    if args.init_only:
        print("Tables created.")
        return

    db = SessionLocal()
    try:
        users = create_test_users(db)
        print(f"Ensured {len(users)} test users.")
        shops, results = load_synthetic_data(
            db, n=args.shops, seed=args.seed, write_csv=args.csv
        )
        print(f"Loaded {len(shops)} shops and {len(results)} reconciliation results.")
        verdicts = {}
        for r in results:
            verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1
        print(f"Verdict counts: {verdicts}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
