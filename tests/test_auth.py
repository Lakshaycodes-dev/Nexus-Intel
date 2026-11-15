"""Authentication endpoint tests (register / login / session / protection)."""

from __future__ import annotations


def _register_payload(**overrides) -> dict:
    payload = {
        "name": "Lakshay Sharma",
        "email": "lakshay@example.com",
        "password": "correct-horse-battery",
        "workspace_name": "Lakshay Retail",
    }
    payload.update(overrides)
    return payload


def test_register_returns_token_and_profile(anon_client, fake_users):
    response = anon_client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"].count(".") == 2

    user = body["user"]
    assert user["email"] == "lakshay@example.com"
    assert user["name"] == "Lakshay Sharma"
    assert user["workspace_name"] == "Lakshay Retail"
    assert "password" not in user
    assert "password_hash" not in user

    stored = list(fake_users.users.values())[0]
    assert stored["password_hash"].startswith("scrypt$")
    assert "correct-horse-battery" not in stored["password_hash"]


def test_register_normalises_email_and_defaults_workspace(anon_client):
    response = anon_client.post(
        "/api/v1/auth/register",
        json=_register_payload(email="  LAKSHAY@Example.COM ", workspace_name="  "),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == "lakshay@example.com"
    assert body["user"]["workspace_name"] == "Lakshay's workspace"


def test_register_rejects_duplicate_email(anon_client):
    assert anon_client.post(
        "/api/v1/auth/register", json=_register_payload()
    ).status_code == 201

    response = anon_client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_weak_password(anon_client):
    response = anon_client.post(
        "/api/v1/auth/register", json=_register_payload(password="short")
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_register_rejects_invalid_email(anon_client):
    response = anon_client.post(
        "/api/v1/auth/register", json=_register_payload(email="not-an-email")
    )
    assert response.status_code == 422


def test_login_succeeds_with_correct_password(anon_client):
    anon_client.post("/api/v1/auth/register", json=_register_payload())

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "lakshay@example.com", "password": "correct-horse-battery"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == "lakshay@example.com"


def test_login_rejects_wrong_password(anon_client):
    anon_client.post("/api/v1/auth/register", json=_register_payload())

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "lakshay@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_does_not_reveal_unknown_email(anon_client):
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever-123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Incorrect email or password."


def test_me_requires_a_token(anon_client):
    response = anon_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_rejects_a_tampered_token(anon_client):
    response = anon_client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"}
    )
    assert response.status_code == 401


def test_me_returns_the_signed_in_user(client, auth_user):
    assert auth_user["email"] == "lakshay@example.com"
    assert auth_user["workspace_name"] == "Lakshay Retail"


def test_analyze_requires_authentication(anon_client):
    response = anon_client.post("/api/v1/analyze", json={"domain": "stripe.com"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_competitor_endpoints_require_authentication(anon_client):
    assert anon_client.get("/api/v1/competitors").status_code == 401
    assert anon_client.get("/api/v1/competitors/stripe.com").status_code == 401


def test_logout_clears_the_session(anon_client):
    response = anon_client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert response.content == b""
