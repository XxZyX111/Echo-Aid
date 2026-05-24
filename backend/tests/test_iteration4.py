"""EchoAid iteration 4 backend tests.

Covers:
- POST /api/mood without note -> {entry, journal_entry: null}
- POST /api/mood with note -> creates linked journal_entry (source='mood_checkin')
- Distress detection attaches AI response on mood w/ anxious + distress note
- Neutral mood + neutral note -> no ai_response
- POST /api/journal with distress content -> ai_response present
- POST /api/journal with neutral content -> no ai_response
- POST /api/journal/{id}/ai-response -> manual generation
- POST /api/journal/{invalid_id}/ai-response -> 404
- GET /api/healing/parks?q=... case-insensitive name/tag search
- GET /api/healing/parks no auth -> no `bookmarked` field
- GET /api/healing/parks with auth -> `bookmarked` boolean on each item
- POST /api/healing/parks/{id}/bookmark toggle behavior
- POST /api/healing/parks/invalid/bookmark -> 404
- GET /api/healing/bookmarks isolation per user
"""

import os
import re
import time
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---------------- Helpers ----------------
def _register_verify_login(prefix: str = "TEST_i4") -> requests.Session:
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    pw = "Test@2026!"
    r = requests.post(
        f"{API}/auth/register",
        json={"name": "Iter4 Tester", "nickname": "Iter4", "email": email, "password": pw, "university": "UI"},
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
    assert "access_token" in s.cookies
    s._email = email  # type: ignore[attr-defined]
    return s


@pytest.fixture(scope="module")
def user_a():
    return _register_verify_login("TEST_i4A")


@pytest.fixture(scope="module")
def user_b():
    return _register_verify_login("TEST_i4B")


# ---------------- Mood: shape + journal mirroring ----------------
class TestMoodResponseShape:
    def test_mood_without_note_returns_null_journal_entry(self, user_a):
        r = user_a.post(f"{API}/mood", json={"mood": "calm"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body.keys()) >= {"entry", "journal_entry"}
        assert body["journal_entry"] is None
        assert body["entry"]["mood"] == "calm"
        assert body["entry"]["entry_id"].startswith("mood_")
        # No back-link since no journal was created
        assert body["entry"].get("linked_journal_id") is None or "linked_journal_id" not in body["entry"]

    def test_mood_with_note_mirrors_to_journal(self, user_a):
        note = "Pagi yang biasa saja, minum kopi"
        r = user_a.post(f"{API}/mood", json={"mood": "calm", "note": note}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        entry = body["entry"]
        journal_entry = body["journal_entry"]
        assert journal_entry is not None, "expected journal_entry when note provided"
        assert journal_entry["source"] == "mood_checkin"
        assert journal_entry["linked_mood_id"] == entry["entry_id"]
        assert entry["linked_journal_id"] == journal_entry["entry_id"]
        assert journal_entry["content"] == note
        assert journal_entry["mood"] == "calm"
        assert journal_entry["entry_id"].startswith("jrn_")
        # Calm + neutral note -> should NOT have ai_response
        assert "ai_response" not in journal_entry or not journal_entry.get("ai_response"), (
            f"calm/neutral entry should not have ai_response: {journal_entry}"
        )

        # Verify journal listing surfaces it with source=mood_checkin
        jr = user_a.get(f"{API}/journal", timeout=20)
        assert jr.status_code == 200
        items = jr.json()["items"]
        match = next((i for i in items if i["entry_id"] == journal_entry["entry_id"]), None)
        assert match is not None, "mirrored journal entry should be listed"
        assert match["source"] == "mood_checkin"

    def test_mood_anxious_with_distress_note_attaches_ai(self, user_a):
        note = "Saya merasa sangat cemas dan stres menjelang ujian besok, ga bisa tidur"
        t0 = time.time()
        r = user_a.post(f"{API}/mood", json={"mood": "anxious", "note": note}, timeout=120)
        print(f"[anxious+distress mood took {time.time()-t0:.1f}s]")
        assert r.status_code == 200, r.text
        body = r.json()
        journal = body["journal_entry"]
        assert journal is not None
        assert journal["source"] == "mood_checkin"
        # iter4b: AI response is now async — initial response should be pending OR already populated
        entry_id = journal["entry_id"]
        deadline = time.time() + 30
        final = journal
        while time.time() < deadline:
            if final.get("ai_response_status") == "ok" and final.get("ai_response"):
                break
            time.sleep(2)
            jr = user_a.get(f"{API}/journal", timeout=20)
            items = jr.json()["items"]
            final = next((i for i in items if i["entry_id"] == entry_id), final)
        assert final.get("ai_response"), f"expected ai_response after polling for anxious mood: {final}"
        assert isinstance(final["ai_response"], str) and len(final["ai_response"].strip()) > 20
        assert final.get("ai_response_at"), "ai_response_at timestamp missing"


# ---------------- Journal: AI auto-attach + manual trigger ----------------
class TestJournalAIAttachment:
    def test_journal_with_distress_content_attaches_ai(self, user_a):
        body = {"mode": "text", "content": "Saya merasa sangat sedih dan putus asa hari ini, lelah sekali.", "mood": "low"}
        t0 = time.time()
        r = user_a.post(f"{API}/journal", json=body, timeout=120)
        print(f"[journal distress took {time.time()-t0:.1f}s]")
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["source"] == "journal"
        # iter4b: AI response is now async — poll for completion
        entry_id = entry["entry_id"]
        deadline = time.time() + 30
        final = entry
        while time.time() < deadline:
            if final.get("ai_response_status") == "ok" and final.get("ai_response"):
                break
            time.sleep(2)
            jr = user_a.get(f"{API}/journal", timeout=20)
            items = jr.json()["items"]
            final = next((i for i in items if i["entry_id"] == entry_id), final)
        assert final.get("ai_response"), f"expected ai_response after polling: {final}"
        assert isinstance(final["ai_response"], str) and len(final["ai_response"].strip()) > 20
        assert final.get("ai_response_at")

    def test_journal_neutral_content_no_ai(self, user_a):
        body = {"mode": "text", "content": "Today I had coffee with a friend at the cafe.", "mood": "neutral"}
        r = user_a.post(f"{API}/journal", json=body, timeout=30)
        assert r.status_code == 200, r.text
        entry = r.json()
        assert "ai_response" not in entry or not entry.get("ai_response"), (
            f"neutral entry should not have ai_response: {entry}"
        )
        # stash for manual trigger test
        user_a._neutral_journal_id = entry["entry_id"]  # type: ignore[attr-defined]

    def test_manual_ai_response_generation(self, user_a):
        entry_id = getattr(user_a, "_neutral_journal_id", None)
        assert entry_id, "neutral journal id must be set by prior test"
        t0 = time.time()
        r = user_a.post(f"{API}/journal/{entry_id}/ai-response", timeout=120)
        print(f"[manual AI took {time.time()-t0:.1f}s]")
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["entry_id"] == entry_id
        assert isinstance(updated.get("ai_response"), str) and len(updated["ai_response"].strip()) > 10
        assert updated.get("ai_response_at")
        assert "_id" not in updated

    def test_manual_ai_response_wrong_id_404(self, user_a):
        r = user_a.post(f"{API}/journal/jrn_doesnotexist/ai-response", timeout=20)
        assert r.status_code == 404, r.text

    def test_manual_ai_response_requires_auth(self):
        r = requests.post(f"{API}/journal/jrn_any/ai-response", timeout=20)
        assert r.status_code == 401


# ---------------- Healing Map: search + bookmarks ----------------
class TestHealingParksSearch:
    def test_search_by_name_case_insensitive(self):
        r = requests.get(f"{API}/healing/parks", params={"q": "menteng"}, timeout=20)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1, "expected at least 1 park for q=menteng"
        for it in items:
            haystack = (it.get("name", "") + " " + it.get("subtitle", "") + " " + " ".join(it.get("tags", []))).lower()
            assert "menteng" in haystack, f"park {it.get('name')} doesn't match 'menteng': {it}"
        names = {i["name"] for i in items}
        assert "Taman Menteng" in names

    def test_search_no_match_returns_empty(self):
        r = requests.get(f"{API}/healing/parks", params={"q": "zzzz_no_such_park_xyz"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_list_parks_unauth_has_no_bookmarked(self):
        r = requests.get(f"{API}/healing/parks", timeout=20)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert "bookmarked" not in it, f"unauthenticated response should not include 'bookmarked': {it}"

    def test_list_parks_auth_has_bookmarked_field(self, user_b):
        r = user_b.get(f"{API}/healing/parks", timeout=20)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1
        for it in items:
            assert "bookmarked" in it and isinstance(it["bookmarked"], bool), (
                f"each park must include bookmarked bool when authed: {it}"
            )
            assert it["bookmarked"] is False  # fresh user, no bookmarks yet


class TestHealingBookmarks:
    def test_toggle_bookmark_on_and_off(self, user_a):
        # Toggle ON
        r1 = user_a.post(f"{API}/healing/parks/taman_suropati/bookmark", timeout=20)
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert b1["bookmarked"] is True
        assert b1["place_id"] == "taman_suropati"

        # Verify reflected in list
        lr = user_a.get(f"{API}/healing/parks", timeout=20)
        assert lr.status_code == 200
        match = next(i for i in lr.json()["items"] if i["place_id"] == "taman_suropati")
        assert match["bookmarked"] is True

        # Verify shows up in /healing/bookmarks
        br = user_a.get(f"{API}/healing/bookmarks", timeout=20)
        assert br.status_code == 200
        bms = br.json()["items"]
        assert any(b["place_id"] == "taman_suropati" for b in bms)

        # Toggle OFF
        r2 = user_a.post(f"{API}/healing/parks/taman_suropati/bookmark", timeout=20)
        assert r2.status_code == 200, r2.text
        assert r2.json()["bookmarked"] is False

        br2 = user_a.get(f"{API}/healing/bookmarks", timeout=20)
        assert not any(b["place_id"] == "taman_suropati" for b in br2.json()["items"])

    def test_bookmark_invalid_park_404(self, user_a):
        r = user_a.post(f"{API}/healing/parks/invalid_id_xyz/bookmark", timeout=20)
        assert r.status_code == 404, r.text

    def test_bookmarks_isolated_per_user(self, user_a, user_b):
        # user_a bookmarks taman_menteng
        ra = user_a.post(f"{API}/healing/parks/taman_menteng/bookmark", timeout=20)
        assert ra.status_code == 200 and ra.json()["bookmarked"] is True

        # user_b should NOT see user_a's bookmark
        rb = user_b.get(f"{API}/healing/bookmarks", timeout=20)
        assert rb.status_code == 200
        assert not any(b["place_id"] == "taman_menteng" for b in rb.json()["items"]), (
            "user_b leaked user_a's bookmark"
        )
        # And user_b's park listing should show bookmarked=False for that park
        lb = user_b.get(f"{API}/healing/parks", timeout=20)
        match = next(i for i in lb.json()["items"] if i["place_id"] == "taman_menteng")
        assert match["bookmarked"] is False

        # Cleanup
        user_a.post(f"{API}/healing/parks/taman_menteng/bookmark", timeout=20)

    def test_bookmarks_require_auth(self):
        r = requests.post(f"{API}/healing/parks/taman_suropati/bookmark", timeout=20)
        assert r.status_code == 401
        r2 = requests.get(f"{API}/healing/bookmarks", timeout=20)
        assert r2.status_code == 401
