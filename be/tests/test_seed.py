"""Tests for the seed script: init_db, create_test_users, load_synthetic_data."""
from __future__ import annotations

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ReconciliationResult, Shop, User
from app.policy import load_policy
from scripts import seed


EXPECTED_TABLES = {"users", "shops", "reconciliation_results", "refresh_tokens"}


class TestInitDb:
    def test_creates_expected_tables(self):
        eng = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        # nothing yet
        assert set(inspect(eng).get_table_names()) == set()
        seed.init_db_tables(eng)
        tables = set(inspect(eng).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
        eng.dispose()


class TestCreateTestUsers:
    def test_creates_users(self, db_session):
        users = seed.create_test_users(db_session)
        assert len(users) == 4
        emails = {u.email for u in users}
        assert "borrower@udyamcred.test" in emails
        assert all(u.password_hash != "borrowerpass" for u in users)

    def test_is_idempotent(self, db_session):
        seed.create_test_users(db_session)
        seed.create_test_users(db_session)
        assert db_session.query(User).count() == 4

    def test_roles_assigned(self, db_session):
        seed.create_test_users(db_session)
        roles = {u.email: u.role for u in db_session.query(User).all()}
        assert roles["officer@udyamcred.test"] == "officer"
        assert roles["auditor@udyamcred.test"] == "auditor"

    def test_password_is_verifiable(self, db_session):
        from app.auth import verify_password

        seed.create_test_users(db_session)
        user = db_session.query(User).filter_by(email="borrower@udyamcred.test").first()
        assert verify_password("borrowerpass", user.password_hash) is True
        assert verify_password("wrong", user.password_hash) is False


class TestLoadSyntheticData:
    def test_loads_shops_and_results(self, db_session):
        shops, results = seed.load_synthetic_data(db_session, n=10, seed=42)
        assert len(shops) == 10
        assert len(results) == 10
        assert db_session.query(Shop).count() == 10
        assert db_session.query(ReconciliationResult).count() == 10

    def test_verdict_mix(self, db_session):
        _, results = seed.load_synthetic_data(db_session, n=10, seed=42)
        verdicts = [r.verdict for r in results]
        assert verdicts.count("approved") == 4
        assert verdicts.count("flagged") == 6

    def test_results_link_to_shops(self, db_session):
        shops, results = seed.load_synthetic_data(db_session, n=10, seed=42)
        for shop, result in zip(shops, results):
            assert result.shop_id == shop.id
            assert result.verdict is not None

    def test_replacement_on_reload(self, db_session):
        seed.load_synthetic_data(db_session, n=10, seed=42)
        assert db_session.query(Shop).count() == 10
        # Reloading with the same shop_ids replaces rather than duplicates.
        seed.load_synthetic_data(db_session, n=10, seed=42)
        assert db_session.query(Shop).count() == 10
        assert db_session.query(ReconciliationResult).count() == 10

    def test_pair_case_preserved_in_db(self, db_session):
        seed.load_synthetic_data(db_session, n=10, seed=42)
        s0 = db_session.query(Shop).filter_by(shop_id=0).first()
        s1 = db_session.query(Shop).filter_by(shop_id=1).first()
        assert s0.upi_turnover == s1.upi_turnover
        v0 = db_session.query(ReconciliationResult).filter_by(shop_id=s0.id).first().verdict
        v1 = db_session.query(ReconciliationResult).filter_by(shop_id=s1.id).first().verdict
        assert v0 == "approved"
        assert v1 == "flagged"

    def test_csv_export(self, db_session, tmp_path):
        import pandas as pd

        csv_path = tmp_path / "shops.csv"
        seed.load_synthetic_data(db_session, n=10, seed=42, write_csv=str(csv_path))
        assert csv_path.exists()
        df = pd.read_csv(csv_path)
        assert len(df) == 10
        assert "shop_id" in df.columns
        assert "gstin" in df.columns
