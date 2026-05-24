"""EchoAid backend API tests.

Covers: auth (register/login/me/logout), mood, journal, healing parks,
meditations, doctors, bookings, chat (Claude), profile, guardians, settings.
"""

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://echoaid-mental.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@echoaid.com"
ADMIN_PASSWORD = "Admin@EchoAid2026"


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies, f"access_token cookie not set; cookies={dict(s.cookies)}"
    return s


@pytest.fixture(scope="module")
def new_user_session():
    """Register, verify email (via dev_verification_url), then login. Returns authed session."""
    import re as _re
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:8]}@echoaid.com"
    pw = "Test@2026!"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": "Test User", "nickname": "Tester", "email": email, "password": pw, "university": "UI"},
        timeout=20,
    )
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    body = r.json()
    assert body.get("ok") is True
    assert body.get("email") == email
    assert body.get("email_verified") is False
    # In testing mode, dev_verification_url is surfaced
    dev_url = body.get("dev_verification_url")
    assert dev_url, f"expected dev_verification_url in register response: {body}"
    m = _re.search(r"[?&]token=([^&]+)", dev_url)
    assert m, f"could not parse token: {dev_url}"
    vt = m.group(1)
    vr = requests.post(f"{API}/auth/verify-email", json={"token": vt}, timeout=20)
    assert vr.status_code == 200, vr.text
    # Login -> sets access_token cookie
    lr = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
    assert lr.status_code == 200, lr.text
    assert "access_token" in s.cookies
    s.email = email  # type: ignore[attr-defined]
    s.password = pw  # type: ignore[attr-defined]
    return s


# ---------------- Health ----------------
def test_root_health():
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    assert r.json().get("ok") is True


# ---------------- Auth ----------------
class TestAuth:
    def test_register_sets_cookie(self, new_user_session):
        # After register+verify+login flow, cookie is set
        assert "access_token" in new_user_session.cookies

    def test_me_with_cookie(self, new_user_session):
        r = new_user_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        u = r.json()["user"]
        assert u["email"] == new_user_session.email
        assert "password_hash" not in u

    def test_me_without_cookie_returns_401(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_admin_login(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["user"]["email"] == ADMIN_EMAIL

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_duplicate_register(self, new_user_session):
        r = requests.post(
            f"{API}/auth/register",
            json={"name": "Dup", "email": new_user_session.email, "password": "Test@2026!"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_logout_clears_cookie(self):
        import re as _re
        s = requests.Session()
        email = f"logout_{uuid.uuid4().hex[:8]}@echoaid.com"
        pw = "Test@2026!"
        rr = requests.post(f"{API}/auth/register", json={"name": "L", "email": email, "password": pw}, timeout=10)
        assert rr.status_code == 200
        token = _re.search(r"[?&]token=([^&]+)", rr.json()["dev_verification_url"]).group(1)
        assert requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=10).status_code == 200
        assert s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=10).status_code == 200
        assert s.get(f"{API}/auth/me", timeout=10).status_code == 200
        r = s.post(f"{API}/auth/logout", timeout=10)
        assert r.status_code == 200
        s.cookies.clear()
        assert s.get(f"{API}/auth/me", timeout=10).status_code == 401


# ---------------- Mood ----------------
class TestMood:
    def test_create_and_list_mood(self, new_user_session):
        # Iter4: response now {entry, journal_entry}; with a note, journal_entry is created.
        r = new_user_session.post(f"{API}/mood", json={"mood": "calm", "note": "TEST_mood"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "entry" in body and "journal_entry" in body
        entry = body["entry"]
        assert entry["mood"] == "calm"
        assert entry["note"] == "TEST_mood"
        assert entry["entry_id"].startswith("mood_")

        r2 = new_user_session.get(f"{API}/mood", timeout=10)
        assert r2.status_code == 200
        items = r2.json()["items"]
        assert any(i["entry_id"] == entry["entry_id"] for i in items)

    def test_invalid_mood_value(self, new_user_session):
        r = new_user_session.post(f"{API}/mood", json={"mood": "ecstatic"}, timeout=10)
        assert r.status_code == 422

    def test_mood_requires_auth(self):
        r = requests.post(f"{API}/mood", json={"mood": "calm"}, timeout=10)
        assert r.status_code == 401


# ---------------- Journal ----------------
class TestJournal:
    def test_create_and_list_journal(self, new_user_session):
        r = new_user_session.post(
            f"{API}/journal",
            json={"mode": "text", "content": "TEST_journal content", "mood": "calm"},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["content"] == "TEST_journal content"
        assert entry["mode"] == "text"

        r2 = new_user_session.get(f"{API}/journal", timeout=10)
        assert r2.status_code == 200
        assert any(i["entry_id"] == entry["entry_id"] for i in r2.json()["items"])


# ---------------- Healing parks ----------------
class TestHealing:
    def test_list_parks(self):
        r = requests.get(f"{API}/healing/parks", timeout=10)
        assert r.status_code == 200
        items = r.json()["items"]
        names = {i["name"] for i in items}
        assert {"Taman Menteng", "Taman Suropati", "Lapangan Banteng"}.issubset(names)


# ---------------- Meditations ----------------
class TestMeditations:
    def test_list_meditations(self):
        r = requests.get(f"{API}/meditations", timeout=10)
        assert r.status_code == 200
        ids = {i["meditation_id"] for i in r.json()["items"]}
        assert "med_478" in ids

    def test_get_meditation_detail(self):
        r = requests.get(f"{API}/meditations/med_478", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["meditation_id"] == "med_478"
        assert isinstance(data["steps"], list) and len(data["steps"]) > 0

    def test_get_meditation_not_found(self):
        r = requests.get(f"{API}/meditations/does_not_exist", timeout=10)
        assert r.status_code == 404


# ---------------- Doctors ----------------
class TestDoctors:
    def test_list_doctors_all(self):
        r = requests.get(f"{API}/doctors", timeout=10)
        assert r.status_code == 200
        assert len(r.json()["items"]) >= 3

    def test_filter_doctors_anxiety(self):
        r = requests.get(f"{API}/doctors", params={"category": "anxiety"}, timeout=10)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        names = {d["name"] for d in items}
        assert "Dr. Elena Vance" in names
        for d in items:
            assert "anxiety" in d["categories"]


# ---------------- Bookings & Chat ----------------
class TestBookingsAndChat:
    def test_create_booking(self, new_user_session):
        r = new_user_session.post(
            f"{API}/bookings",
            json={
                "doctor_id": "doc_elena_vance",
                "date": "2026-02-15",
                "time": "10:00 AM",
                "category": "anxiety",
                "note": "TEST_booking",
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["doctor_name"] == "Dr. Elena Vance"
        assert b["status"] == "confirmed"
        new_user_session.booking_id = b["booking_id"]  # type: ignore[attr-defined]

    def test_booking_invalid_doctor(self, new_user_session):
        r = new_user_session.post(
            f"{API}/bookings",
            json={"doctor_id": "no_such", "date": "2026-02-15", "time": "10:00 AM"},
            timeout=10,
        )
        assert r.status_code == 404

    def test_list_bookings(self, new_user_session):
        r = new_user_session.get(f"{API}/bookings", timeout=10)
        assert r.status_code == 200
        assert len(r.json()["items"]) >= 1

    def test_chat_forbidden_for_other_user(self, new_user_session, admin_session):
        # admin tries to chat using user's booking_id -> should be 403
        booking_id = getattr(new_user_session, "booking_id", None)
        assert booking_id, "booking_id not set"
        r = admin_session.post(
            f"{API}/chat/send",
            json={"booking_id": booking_id, "message": "test"},
            timeout=15,
        )
        assert r.status_code == 403

    def test_chat_send_and_history(self, new_user_session):
        booking_id = getattr(new_user_session, "booking_id", None)
        assert booking_id, "booking_id required"
        r = new_user_session.post(
            f"{API}/chat/send",
            json={"booking_id": booking_id, "message": "Halo dok, saya sedang cemas menghadapi ujian."},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user_message"]["role"] == "user"
        assert data["ai_message"]["role"] == "assistant"
        assert isinstance(data["ai_message"]["content"], str)
        assert len(data["ai_message"]["content"]) > 0

        # History
        time.sleep(0.5)
        h = new_user_session.get(f"{API}/chat/{booking_id}", timeout=10)
        assert h.status_code == 200
        hist = h.json()
        assert hist["booking"]["booking_id"] == booking_id
        assert len(hist["messages"]) >= 2

    def test_chat_history_forbidden_other_user(self, new_user_session, admin_session):
        booking_id = getattr(new_user_session, "booking_id", None)
        r = admin_session.get(f"{API}/chat/{booking_id}", timeout=10)
        assert r.status_code == 403


# ---------------- Profile ----------------
class TestProfile:
    def test_patch_profile_preferences_and_privacy(self, new_user_session):
        r = new_user_session.patch(
            f"{API}/profile",
            json={
                "sanctuary_preferences": {"dark_mode": True, "daily_reminders": False},
                "privacy": {"biometric_lock": True, "journal_encryption": True},
            },
            timeout=10,
        )
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u["sanctuary_preferences"]["dark_mode"] is True
        assert u["privacy"]["biometric_lock"] is True

        # Verify persistence via /me
        r2 = new_user_session.get(f"{API}/auth/me", timeout=10)
        assert r2.json()["user"]["sanctuary_preferences"]["dark_mode"] is True

    def test_add_and_remove_guardian(self, new_user_session):
        r = new_user_session.post(
            f"{API}/profile/guardian",
            json={"name": "Ibu Sari", "relation": "Mother", "phone": "+628111222333"},
            timeout=10,
        )
        assert r.status_code == 200
        guardians = r.json()["user"]["guardian_circle"]
        assert any(g["name"] == "Ibu Sari" for g in guardians)
        gid = next(g["guardian_id"] for g in guardians if g["name"] == "Ibu Sari")

        r2 = new_user_session.delete(f"{API}/profile/guardian/{gid}", timeout=10)
        assert r2.status_code == 200
        guardians_after = r2.json()["user"]["guardian_circle"]
        assert all(g["guardian_id"] != gid for g in guardians_after)


# ---------------- Settings ----------------
class TestSettings:
    def test_patch_settings(self, new_user_session):
        r = new_user_session.patch(
            f"{API}/settings",
            json={"notifications": False, "dark_mode": True, "larger_text": True},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        s = r.json()["user"]["settings"]
        assert s["notifications"] is False
        assert s["dark_mode"] is True
        assert s["larger_text"] is True
