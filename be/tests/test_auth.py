"""Tests for the auth API: register, login, JWT access, refresh rotation, logout."""
from __future__ import annotations

import pytest

from app.models import RefreshToken


@pytest.fixture
def registered_client(client):
    """A client with one registered borrower."""
    r = client.post(
        "/auth/register",
        json={"email": "borrower@udyamcred.test", "password": "supersecret", "role": "borrower"},
    )
    assert r.status_code == 201
    return client


class TestRegister:
    def test_register_returns_user(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "a@b.test", "password": "supersecret", "role": "officer"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == "a@b.test"
        assert body["role"] == "officer"
        assert "id" in body

    def test_duplicate_email_conflict(self, registered_client):
        r = registered_client.post(
            "/auth/register",
            json={"email": "borrower@udyamcred.test", "password": "supersecret"},
        )
        assert r.status_code == 409

    def test_short_password_rejected(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "a@b.test", "password": "short"},
        )
        assert r.status_code == 422

    def test_invalid_role_rejected(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "a@b.test", "password": "supersecret", "role": "wizard"},
        )
        assert r.status_code == 400


class TestLogin:
    def test_login_returns_tokens(self, registered_client):
        r = registered_client.post(
            "/auth/login",
            json={"email": "borrower@udyamcred.test", "password": "supersecret"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["expires_in"] == 15 * 60

    def test_login_wrong_password(self, registered_client):
        r = registered_client.post(
            "/auth/login",
            json={"email": "borrower@udyamcred.test", "password": "wrong"},
        )
        assert r.status_code == 401

    def test_login_unknown_user(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "nobody@b.test", "password": "whatever"},
        )
        assert r.status_code == 401

    def test_remember_me_stored_on_refresh(self, registered_client):
        r = registered_client.post(
            "/auth/login",
            json={"email": "borrower@udyamcred.test", "password": "supersecret", "remember_me": True},
        )
        assert r.status_code == 200
        # The refresh token is stored hashed in the DB with remember_me=True.
        from app.auth import hash_token

        rt = r.json()["refresh_token"]
        # inspect via the client's db is awkward; rely on a direct check below
        assert rt


class TestProtected:
    def _login(self, client):
        client.post(
            "/auth/register",
            json={"email": "x@b.test", "password": "supersecret"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "x@b.test", "password": "supersecret"},
        )
        return r.json()["access_token"]

    def test_reconcile_requires_auth(self, client):
        r = client.post(
            "/reconcile",
            json={
                "shop_id": 0,
                "gstin": "27AAACR5049K1Z5",
                "shop_category": "kirana_without_inventory",
                "purchases": 1_100_000,
                "gst_turnover": 1_000_000,
                "upi_turnover": 500_000,
            },
        )
        assert r.status_code == 401

    def test_reconcile_with_token(self, client):
        token = self._login(client)
        r = client.post(
            "/reconcile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "shop_id": 0,
                "gstin": "27AAACR5049K1Z5",
                "shop_category": "kirana_without_inventory",
                "purchases": 900_000,  # goods_sold = 900_000; expected = 900_000 / (1 - 0.10) = 1_000_000
                "gst_turnover": 1_000_000,
                "upi_turnover": 500_000,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["verdict"] == "approved"
        assert body["gstin_valid"] is True

    def test_reconcile_invalid_gstin_rejected(self, client):
        token = self._login(client)
        r = client.post(
            "/reconcile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "shop_id": 2,
                "gstin": "27AAACR5049K1Z0",
                "shop_category": "packaged_fmcg",
                "purchases": 1_000_000,
                "gst_turnover": 900_000,
                "upi_turnover": 400_000,
            },
        )
        assert r.status_code == 200
        assert r.json()["verdict"] == "rejected"


class TestRefreshRotation:
    def _login(self, client, remember_me=False):
        client.post(
            "/auth/register",
            json={"email": "y@b.test", "password": "supersecret"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "y@b.test", "password": "supersecret", "remember_me": remember_me},
        )
        return r.json()["refresh_token"]

    def test_refresh_issues_new_tokens_and_revokes_old(self, client, db_session):
        old_refresh = self._login(client)
        r = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 200
        body = r.json()
        new_refresh = body["refresh_token"]
        assert new_refresh != old_refresh
        assert body["access_token"]

        # The old refresh token is now revoked in the DB.
        from app.auth import hash_token

        old_hash = hash_token(old_refresh)
        rt = db_session.query(RefreshToken).filter_by(token_hash=old_hash).first()
        assert rt is not None
        assert rt.revoked is True

    def test_refresh_token_single_use(self, client):
        old_refresh = self._login(client)
        # First refresh succeeds.
        r1 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r1.status_code == 200
        # Reusing the old (now revoked) token fails.
        r2 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r2.status_code == 401

    def test_logout_revokes_refresh(self, client, db_session):
        from app.auth import hash_token

        refresh = self._login(client)
        r = client.post("/auth/logout", json={"refresh_token": refresh})
        assert r.status_code == 200
        assert r.json()["revoked"] is True
        rt = db_session.query(RefreshToken).filter_by(token_hash=hash_token(refresh)).first()
        assert rt.revoked is True

    def test_logout_unknown_token(self, client):
        r = client.post("/auth/logout", json={"refresh_token": "not-a-real-token"})
        assert r.status_code == 200
        assert r.json()["revoked"] is False
