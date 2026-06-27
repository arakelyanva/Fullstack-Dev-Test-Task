from fastapi.testclient import TestClient

from app.core.config import settings

API = settings.API_V1_STR


# --- List users: admin + manager allowed, member denied ---


def test_admin_can_list_users(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/users/", headers=superuser_token_headers)
    assert r.status_code == 200


def test_manager_can_list_users(
    client: TestClient, manager_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/users/", headers=manager_token_headers)
    assert r.status_code == 200


def test_member_cannot_list_users(
    client: TestClient, member_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/users/", headers=member_token_headers)
    assert r.status_code == 403


# --- Create user: admin only ---


def test_manager_cannot_create_user(
    client: TestClient, manager_token_headers: dict[str, str]
) -> None:
    payload = {"email": "new@example.com", "password": "changethis123"}
    r = client.post(f"{API}/users/", headers=manager_token_headers, json=payload)
    assert r.status_code == 403


# --- Metrics: admin + manager allowed, member denied ---


def test_manager_can_view_metrics(
    client: TestClient, manager_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/metrics/", headers=manager_token_headers)
    assert r.status_code == 200


def test_member_cannot_view_metrics(
    client: TestClient, member_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/metrics/", headers=member_token_headers)
    assert r.status_code == 403


# --- Own profile: every role can read its own profile ---


def test_member_can_read_own_profile(
    client: TestClient, member_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/users/me", headers=member_token_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "member"


# --- Privilege-escalation guard: self-update cannot change role ---


def test_member_cannot_escalate_role_via_update_me(
    client: TestClient, member_token_headers: dict[str, str]
) -> None:
    # `role` is not part of UserUpdateMe, so it must be ignored, not applied.
    r = client.patch(
        f"{API}/users/me",
        headers=member_token_headers,
        json={"full_name": "Member", "role": "admin"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "member"
