import base64
import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.rag.extractor import DocumentExtractor

client = TestClient(app)


def _make_unsigned_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.fake_sig"


def test_config_has_no_hardcoded_smtp_credentials():
    assert settings.SMTP_USER == ""
    assert settings.SMTP_PASSWORD == ""
    assert settings.SMTP_FROM_EMAIL == ""
    assert "qzzx" not in settings.SMTP_PASSWORD


def test_google_auth_rejects_missing_or_forged_tokens():
    # Tokenless email payload must be rejected
    res_no_token = client.post("/api/auth/google", json={"email": "victim@example.com", "name": "Victim"})
    assert res_no_token.status_code == 400

    # Unsigned/forged JWT payload must be rejected
    forged = _make_unsigned_jwt({"email": "victim@example.com", "sub": "123", "iss": "accounts.google.com"})
    res_forged = client.post("/api/auth/google", json={"credential": forged})
    assert res_forged.status_code == 400


def test_signup_duplicate_prevention_and_signin_hardening():
    email = "alice_sec@example.com"
    res = client.post("/api/auth/signup", json={
        "name": "Alice",
        "email": email,
        "password": "secretPassword1"
    })
    assert res.status_code == 200
    token1 = res.json()["access_token"]
    assert token1

    # Attempt duplicate signup with a DIFFERENT password to overwrite Alice's password
    dup = client.post("/api/auth/signup", json={
        "name": "Attacker",
        "email": email,
        "password": "attackerPassword9"
    })
    assert dup.status_code == 400
    assert "already exists" in dup.json()["detail"].lower()

    # Attacker password must NOT work
    bad_login = client.post("/api/auth/signin", json={
        "email": email,
        "password": "attackerPassword9"
    })
    assert bad_login.status_code == 400

    # Alice's original password must still work
    good_login = client.post("/api/auth/signin", json={
        "email": email,
        "password": "secretPassword1"
    })
    assert good_login.status_code == 200


def test_otp_passwordless_flow_and_empty_password_bypass_blocked():
    email = "otp_user@example.com"
    otp_res = client.post("/api/auth/send-otp", json={
        "email": email,
        "name": "OTP User",
        "purpose": "signup"
    })
    assert otp_res.status_code == 200
    otp_data = otp_res.json()
    assert "dev_otp" in otp_data
    code = otp_data["dev_otp"]

    # Wrong code fails
    bad_verify = client.post("/api/auth/verify-otp", json={"email": email, "otp": "000000"})
    assert bad_verify.status_code == 400

    # Valid code verifies and issues session
    verify_res = client.post("/api/auth/verify-otp", json={
        "email": email,
        "otp": code,
        "name": "OTP User"
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["user"]["email"] == email

    # Passwordless account MUST reject empty password signin attempt
    empty_pw_login = client.post("/api/auth/signin", json={"email": email, "password": ""})
    assert empty_pw_login.status_code == 400


def test_forgot_and_reset_password_with_otp():
    email = "reset_user@example.com"
    client.post("/api/auth/signup", json={
        "name": "Reset User",
        "email": email,
        "password": "oldPassword1"
    })

    forgot = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    reset_code = forgot.json()["dev_otp"]

    reset_res = client.post("/api/auth/reset-password", json={
        "email": email,
        "otp": reset_code,
        "new_password": "newPassword2"
    })
    assert reset_res.status_code == 200

    # Old password fails, new password succeeds
    assert client.post("/api/auth/signin", json={"email": email, "password": "oldPassword1"}).status_code == 400
    assert client.post("/api/auth/signin", json={"email": email, "password": "newPassword2"}).status_code == 200


def test_ssrf_blocks_private_and_loopback_urls():
    for bad_url in [
        "http://127.0.0.1:8000/api/health",
        "http://localhost:5173",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/admin",
    ]:
        with pytest.raises(ValueError):
            DocumentExtractor.extract_from_url(bad_url)

        res = client.post("/api/documents/url", json={"url": bad_url})
        assert res.status_code == 400


def test_settings_update_requires_authentication():
    anon_client = TestClient(app)
    cur = anon_client.get("/api/settings")
    assert cur.status_code == 200
    payload = cur.json()

    # Unauthenticated POST must fail with 401
    unauth = anon_client.post("/api/settings", json=payload)
    assert unauth.status_code == 401

    # Authenticated user can update valid bounds
    signup = anon_client.post("/api/auth/signup", json={
        "name": "Settings Admin",
        "email": "settings_admin@example.com",
        "password": "password123"
    })
    token = signup.json()["access_token"]
    payload["retrieval_top_k"] = 12
    auth_res = anon_client.post(
        "/api/settings",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["retrieval_top_k"] == 12
