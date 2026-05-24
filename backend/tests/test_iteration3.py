"""EchoAid iteration 3 backend tests — Weekly AI Insights.

Covers:
- GET /api/insights/weekly with no prior generation → insight=null, stats, is_stale=true
- POST /api/insights/weekly with empty history → 400 with Indonesian message
- POST /api/insights/weekly after seeding moods → returns generated insight with stats
- GET /api/insights/weekly after generation → cached insight, is_stale=false
- POST /api/insights/weekly second call → new insight doc persisted, returned by GET
- Auth required on both endpoints (401 without cookie)
- Cross-tenant isolation between users
"""

import os
import re
import time
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

VALID_MOODS = ["grateful", "calm", "neutral", "low", "anxious"]


# ---------------- Helpers ----------------
def _register_verify_login(prefix: str = "TEST_ins") -> requests.Session:
    """Register a fresh user, verify email via dev_verification_url, login. Returns Session with cookies."""
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    pw = "Test@2026!"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": "Insight Tester", "nickname": "Ins", "email": email, "password": pw, "university": "UI"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    dev_url = r.json().get("dev_verification_url")
    assert dev_url, f"dev_verification_url missing: {r.json()}"
    m = re.search(r"[?&]token=([^&]+)", dev_url)
    assert m, dev_url
    token = m.group(1)
    vr = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20)
    assert vr.status_code == 200, vr.text

    s = requests.Session()
    lr = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
    assert lr.status_code == 200, lr.text
    assert "access_token" in s.cookies
    s._email = email  # type: ignore[attr-defined]
    return s


def _seed_moods(session: requests.Session, moods_with_notes):
    created = []
    for mood, note in moods_with_notes:
        r = session.post(f"{API}/mood", json={"mood": mood, "note": note}, timeout=20)
        assert r.status_code == 200, r.text
        created.append(r.json())
    return created


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def user_a():
    return _register_verify_login("TEST_insA")


@pytest.fixture(scope="module")
def user_b():
    return _register_verify_login("TEST_insB")


# ---------------- Tests ----------------
class TestWeeklyInsightsAuth:
    def test_get_insights_requires_auth(self):
        r = requests.get(f"{API}/insights/weekly", timeout=20)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"

    def test_post_insights_requires_auth(self):
        r = requests.post(f"{API}/insights/weekly", timeout=20)
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


class TestWeeklyInsightsFlow:
    """End-to-end flow for one user: empty → seed → generate → cached → regenerate."""

    def test_01_get_before_generation_returns_null_insight_with_stats(self, user_a):
        r = user_a.get(f"{API}/insights/weekly", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["insight"] is None
        assert data["is_stale"] is True
        stats = data["stats"]
        assert stats["mood_entries"] == 0
        assert stats["journal_entries"] == 0
        assert stats["mood_counts"] == {}
        assert stats["avg_mood_score"] is None
        assert stats["dominant_mood"] is None

    def test_02_post_with_empty_history_returns_400(self, user_a):
        r = user_a.post(f"{API}/insights/weekly", timeout=20)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        # Indonesian helpful message
        assert any(kw in detail.lower() for kw in ["mood", "jurnal", "belum"]), f"unexpected detail: {detail}"

    def test_03_post_after_seeding_returns_insight(self, user_a):
        # Seed a variety of mood entries so stats are meaningful
        _seed_moods(
            user_a,
            [
                ("calm", "Pagi yang tenang setelah meditasi"),
                ("grateful", "Bersyukur lulus quiz"),
                ("anxious", "Deg-degan menjelang presentasi"),
                ("calm", "Berhasil journaling 10 menit"),
                ("low", "Capek banget hari ini"),
            ],
        )

        t0 = time.time()
        r = user_a.post(f"{API}/insights/weekly", timeout=120)
        elapsed = time.time() - t0
        print(f"[insight gen took {elapsed:.1f}s]")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_stale"] is False
        stats = body["stats"]
        assert stats["mood_entries"] == 5
        assert stats["mood_counts"].get("calm") == 2
        assert stats["mood_counts"].get("grateful") == 1
        assert stats["mood_counts"].get("anxious") == 1
        assert stats["mood_counts"].get("low") == 1
        # avg: (4 + 5 + 1 + 4 + 2) / 5 = 3.2
        assert abs(stats["avg_mood_score"] - 3.2) < 0.01
        assert stats["dominant_mood"] == "calm"

        insight = body["insight"]
        assert insight is not None
        assert insight["insight_id"].startswith("ins_")
        assert isinstance(insight["content"], str) and len(insight["content"].strip()) > 30, (
            f"AI content too short: {insight.get('content')!r}"
        )
        assert insight["stats"] == stats
        assert "created_at" in insight
        # Should not leak Mongo _id
        assert "_id" not in insight

        # Stash for next test
        user_a._first_insight_id = insight["insight_id"]  # type: ignore[attr-defined]
        user_a._first_created_at = insight["created_at"]  # type: ignore[attr-defined]

    def test_04_get_after_generation_returns_cached(self, user_a):
        r = user_a.get(f"{API}/insights/weekly", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_stale"] is False
        insight = body["insight"]
        assert insight is not None
        assert insight["insight_id"] == getattr(user_a, "_first_insight_id")
        assert "_id" not in insight
        # stats reflect current data (still 5 moods)
        assert body["stats"]["mood_entries"] == 5

    def test_05_post_second_time_persists_new_doc(self, user_a):
        # Iter4 update: server now throttles POST /api/insights/weekly within 24h
        # and returns the existing cached doc (with throttled=true). Validate that
        # the existing doc is returned and no new Claude call is performed.
        first_id = getattr(user_a, "_first_insight_id")
        first_created_at = getattr(user_a, "_first_created_at")

        time.sleep(1.2)
        t0 = time.time()
        r = user_a.post(f"{API}/insights/weekly", timeout=120)
        elapsed = time.time() - t0
        print(f"[2nd insight gen took {elapsed:.1f}s]")
        assert r.status_code == 200, r.text
        body = r.json()
        returned_insight = body["insight"]
        assert returned_insight["insight_id"] == first_id, (
            "expected throttled cached insight on second POST within 24h"
        )
        assert returned_insight["created_at"] == first_created_at
        # Throttled response should be fast (< 2s, no Claude call)
        assert elapsed < 3.0, f"throttled call should be fast, took {elapsed:.1f}s"
        # Optional throttled flag
        if "throttled" in body:
            assert body["throttled"] is True

        # GET should still return that same doc
        gr = user_a.get(f"{API}/insights/weekly", timeout=20)
        assert gr.status_code == 200
        assert gr.json()["insight"]["insight_id"] == first_id


class TestWeeklyInsightsIsolation:
    """User B must not see User A's insights."""

    def test_user_b_has_no_insights_after_user_a_generated(self, user_a, user_b):
        # Ensure user_a has at least one insight (depend on prior class? - run independently to be safe)
        # First check user_b GET is empty
        rb = user_b.get(f"{API}/insights/weekly", timeout=20)
        assert rb.status_code == 200
        body = rb.json()
        # user_b never seeded moods nor generated, so insight should be None and stats zero
        assert body["insight"] is None, f"user_b should not see user_a's insight: {body}"
        assert body["is_stale"] is True
        assert body["stats"]["mood_entries"] == 0

    def test_user_b_post_without_history_still_400(self, user_b):
        r = user_b.post(f"{API}/insights/weekly", timeout=20)
        assert r.status_code == 400, r.text
