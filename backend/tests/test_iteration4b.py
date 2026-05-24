"""EchoAid iteration 4b backend tests - async AI supportive response.

Verifies:
- POST /api/mood with distress note returns FAST (<3s); journal_entry has ai_response_status='pending', no ai_response yet
- After polling GET /api/journal, ai_response_status becomes 'ok' and ai_response is populated
- POST /api/mood with neutral note has NO ai_response_status field at all
- POST /api/journal with distress content returns fast with status='pending', then polled to 'ok'
- POST /api/journal/{id}/ai-response (manual) remains SYNCHRONOUS - returns ai_response in same call
"""

import os
import re
import time
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

FAST_RESPONSE_SEC = 3.0  # POST /mood and /journal must return within this
POLL_TIMEOUT_SEC = 30.0
POLL_INTERVAL_SEC = 2.0


def _register_verify_login(prefix: str = "TEST_i4b") -> requests.Session:
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    pw = "Test@2026!"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": "Iter4b Tester", "nickname": "Iter4b", "email": email, "password": pw, "university": "UI"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    dev_url = r.json().get("dev_verification_url")
    assert dev_url
    token = re.search(r"[?&]token=([^&]+)", dev_url).group(1)
    vr = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20)
    assert vr.status_code == 200, vr.text
    s = requests.Session()
    lr = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
    assert lr.status_code == 200, lr.text
    return s


@pytest.fixture(scope="module")
def user():
    return _register_verify_login("TEST_i4b")


def _poll_journal_entry(session, entry_id, timeout=POLL_TIMEOUT_SEC):
    """Poll GET /api/journal until ai_response_status is non-pending or timeout."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = session.get(f"{API}/journal", timeout=20)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        match = next((i for i in items if i["entry_id"] == entry_id), None)
        if match:
            last = match
            status = match.get("ai_response_status")
            if status == "ok":
                return match
            if status == "failed":
                return match
        time.sleep(POLL_INTERVAL_SEC)
    return last


class TestAsyncMoodAI:
    def test_mood_distress_returns_fast_pending(self, user):
        note = "Saya merasa sangat cemas dan stres menjelang ujian besok, ga bisa tidur, putus asa"
        t0 = time.perf_counter()
        r = user.post(f"{API}/mood", json={"mood": "anxious", "note": note}, timeout=30)
        elapsed = time.perf_counter() - t0
        print(f"[mood distress POST took {elapsed:.2f}s]")
        assert r.status_code == 200, r.text
        assert elapsed < FAST_RESPONSE_SEC, (
            f"POST /mood took {elapsed:.2f}s — must be <{FAST_RESPONSE_SEC}s (Claude should run async, not block)"
        )
        body = r.json()
        journal = body["journal_entry"]
        assert journal is not None
        assert journal.get("ai_response_status") == "pending", (
            f"expected ai_response_status='pending', got: {journal}"
        )
        # ai_response must NOT be populated yet (background task still running)
        assert not journal.get("ai_response"), (
            f"ai_response should not be populated immediately: {journal}"
        )

        # Poll for completion
        entry_id = journal["entry_id"]
        final = _poll_journal_entry(user, entry_id)
        assert final is not None, "entry vanished from journal list"
        assert final.get("ai_response_status") == "ok", (
            f"after polling, expected status='ok', got: {final.get('ai_response_status')} — full: {final}"
        )
        assert isinstance(final.get("ai_response"), str) and len(final["ai_response"].strip()) > 20, (
            f"ai_response should be populated after async completion: {final}"
        )
        assert final.get("ai_response_at"), "ai_response_at timestamp missing"

    def test_mood_neutral_no_status_field(self, user):
        r = user.post(f"{API}/mood", json={"mood": "calm", "note": "Today I had coffee with a friend"}, timeout=30)
        assert r.status_code == 200, r.text
        journal = r.json()["journal_entry"]
        assert journal is not None
        assert "ai_response_status" not in journal, (
            f"neutral entry should have NO ai_response_status field: {journal}"
        )
        assert not journal.get("ai_response")

    def test_mood_without_note_no_journal(self, user):
        r = user.post(f"{API}/mood", json={"mood": "grateful"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["journal_entry"] is None


class TestAsyncJournalAI:
    def test_journal_distress_returns_fast_pending(self, user):
        body = {"mode": "text", "content": "Saya merasa sangat sedih dan putus asa hari ini, lelah sekali, hopeless", "mood": "low"}
        t0 = time.perf_counter()
        r = user.post(f"{API}/journal", json=body, timeout=30)
        elapsed = time.perf_counter() - t0
        print(f"[journal distress POST took {elapsed:.2f}s]")
        assert r.status_code == 200, r.text
        assert elapsed < FAST_RESPONSE_SEC, (
            f"POST /journal took {elapsed:.2f}s — must be <{FAST_RESPONSE_SEC}s"
        )
        entry = r.json()
        assert entry.get("ai_response_status") == "pending"
        assert not entry.get("ai_response")

        final = _poll_journal_entry(user, entry["entry_id"])
        assert final is not None
        assert final.get("ai_response_status") == "ok", f"got status={final.get('ai_response_status')}, entry={final}"
        assert isinstance(final.get("ai_response"), str) and len(final["ai_response"].strip()) > 20
        assert final.get("ai_response_at")

    def test_journal_neutral_no_status(self, user):
        body = {"mode": "text", "content": "Hari ini biasa saja, ngerjain tugas kuliah.", "mood": "neutral"}
        r = user.post(f"{API}/journal", json=body, timeout=20)
        assert r.status_code == 200
        entry = r.json()
        assert "ai_response_status" not in entry
        assert not entry.get("ai_response")
        # Save for manual test
        user._neutral_id = entry["entry_id"]  # type: ignore


class TestManualAISynchronous:
    def test_manual_endpoint_remains_synchronous(self, user):
        entry_id = getattr(user, "_neutral_id", None)
        assert entry_id, "must run after test_journal_neutral_no_status"
        t0 = time.perf_counter()
        r = user.post(f"{API}/journal/{entry_id}/ai-response", timeout=120)
        elapsed = time.perf_counter() - t0
        print(f"[manual AI took {elapsed:.2f}s]")
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["entry_id"] == entry_id
        # Synchronous: ai_response must be present in the SAME response
        assert isinstance(updated.get("ai_response"), str) and len(updated["ai_response"].strip()) > 20, (
            f"manual endpoint must return ai_response synchronously: {updated}"
        )
        assert updated.get("ai_response_at")
        # Should NOT be 'pending' — manual is synchronous
        assert updated.get("ai_response_status") != "pending", (
            f"manual response should not be pending: {updated}"
        )
