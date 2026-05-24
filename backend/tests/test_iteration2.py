"""EchoAid iteration 2 backend tests.

Covers:
- Email verification flow (register without auto-login, verify-email, resend-verification)
- Login blocked for unverified users (HTTP 403 + code=email_not_verified)
- Admin login still works (seeded with email_verified=True)
- Healing parks geolocation sorting (haversine distance)
- WebSocket chat /api/ws/chat/{booking_id} (auth, ping/pong, streaming AI response)
"""

import asyncio
import json
import os
import re
import ssl
import time
import uuid
from urllib.parse import urlparse

import pytest
import requests
import websockets

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

# WS URL: convert https -> wss / http -> ws
_parsed = urlparse(BASE_URL)
WS_SCHEME = "wss" if _parsed.scheme == "https" else "ws"
WS_BASE = f"{WS_SCHEME}://{_parsed.netloc}"

ADMIN_EMAIL = "admin@echoaid.com"
ADMIN_PASSWORD = "Admin@EchoAid2026"


# ---------------- Helpers / Fixtures ----------------
def _register_user(email: str, name: str = "Verify Tester", password: str = "Test@2026!"):
    r = requests.post(
        f"{API}/auth/register",
        json={"name": name, "nickname": "VT", "email": email, "password": password, "university": "UI"},
        timeout=20,
    )
    return r


def _extract_token_from_url(url: str) -> str:
    m = re.search(r"[?&]token=([^&]+)", url)
    assert m, f"could not parse token from dev_verification_url: {url}"
    return m.group(1)


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies
    return s


# ---------------- Email Verification ----------------
class TestEmailVerification:
    """Email verification flow with Resend testing mode (dev_verification_url surfaced)."""

    def test_register_does_not_auto_login_and_returns_dev_link(self):
        email = f"TEST_verify_{uuid.uuid4().hex[:8]}@example.com"
        r = _register_user(email)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["email"] == email.lower()
        assert data["email_verified"] is False
        # SENDER_EMAIL is onboarding@resend.dev -> testing mode -> dev_verification_url returned
        assert "dev_verification_url" in data, f"dev_verification_url missing in testing mode: {data}"
        assert "/verify-email?token=" in data["dev_verification_url"]
        # No cookie should be set on register
        assert "access_token" not in r.cookies, f"register should not auto-login, cookies={dict(r.cookies)}"

    def test_login_blocked_for_unverified_user(self):
        email = f"TEST_unverified_{uuid.uuid4().hex[:8]}@example.com"
        pw = "Test@2026!"
        r = _register_user(email, password=pw)
        assert r.status_code == 200
        # Try login - should be 403 with email_not_verified
        lr = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
        assert lr.status_code == 403, f"expected 403 got {lr.status_code}: {lr.text}"
        body = lr.json()
        detail = body.get("detail") or body
        # detail can be wrapped under "detail" key by FastAPI
        if isinstance(detail, dict):
            assert detail.get("code") == "email_not_verified", f"expected code=email_not_verified, got {detail}"
            assert detail.get("email") == email.lower()
        else:
            pytest.fail(f"expected dict detail with code, got: {body}")

    def test_verify_email_success_then_login(self):
        email = f"TEST_flow_{uuid.uuid4().hex[:8]}@example.com"
        pw = "Test@2026!"
        r = _register_user(email, password=pw)
        assert r.status_code == 200
        token = _extract_token_from_url(r.json()["dev_verification_url"])

        # Verify
        vr = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20)
        assert vr.status_code == 200, vr.text
        vd = vr.json()
        assert vd["ok"] is True
        assert vd["email"] == email.lower()

        # Now login should succeed
        s = requests.Session()
        lr = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
        assert lr.status_code == 200, lr.text
        assert "access_token" in s.cookies
        ldata = lr.json()
        assert ldata["user"]["email"] == email.lower()
        assert ldata["user"]["email_verified"] is True

        # /auth/me works
        me = s.get(f"{API}/auth/me", timeout=20)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == email.lower()

    def test_verify_email_invalid_token(self):
        r = requests.post(f"{API}/auth/verify-email", json={"token": "definitely-not-real-token-xyz"}, timeout=20)
        assert r.status_code == 400, r.text
        assert "detail" in r.json()

    def test_verify_email_empty_token(self):
        r = requests.post(f"{API}/auth/verify-email", json={"token": ""}, timeout=20)
        assert r.status_code == 400

    def test_verify_email_already_used(self):
        email = f"TEST_used_{uuid.uuid4().hex[:8]}@example.com"
        r = _register_user(email)
        token = _extract_token_from_url(r.json()["dev_verification_url"])
        # Use once
        vr1 = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20)
        assert vr1.status_code == 200
        # Use again - should fail
        vr2 = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20)
        assert vr2.status_code == 400
        assert "sudah digunakan" in vr2.json().get("detail", "").lower() or "digunakan" in vr2.json().get("detail", "").lower()

    def test_resend_verification_issues_new_token_and_invalidates_old(self):
        email = f"TEST_resend_{uuid.uuid4().hex[:8]}@example.com"
        r = _register_user(email)
        old_token = _extract_token_from_url(r.json()["dev_verification_url"])

        # Resend
        rr = requests.post(f"{API}/auth/resend-verification", json={"email": email}, timeout=20)
        assert rr.status_code == 200, rr.text
        rd = rr.json()
        assert rd["ok"] is True
        assert "dev_verification_url" in rd, f"expected new dev_verification_url, got: {rd}"
        new_token = _extract_token_from_url(rd["dev_verification_url"])
        assert new_token != old_token

        # Old token should now be invalidated (marked used)
        old_resp = requests.post(f"{API}/auth/verify-email", json={"token": old_token}, timeout=20)
        assert old_resp.status_code == 400, f"old token should be invalid: {old_resp.text}"

        # New token works
        new_resp = requests.post(f"{API}/auth/verify-email", json={"token": new_token}, timeout=20)
        assert new_resp.status_code == 200

    def test_resend_for_unknown_email_does_not_leak(self):
        # Should return ok=True regardless to avoid email enumeration
        r = requests.post(
            f"{API}/auth/resend-verification",
            json={"email": f"nobody_{uuid.uuid4().hex[:8]}@example.com"},
            timeout=20,
        )
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_resend_for_already_verified_returns_already_verified(self):
        # Register + verify
        email = f"TEST_already_{uuid.uuid4().hex[:8]}@example.com"
        r = _register_user(email)
        token = _extract_token_from_url(r.json()["dev_verification_url"])
        assert requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20).status_code == 200
        # Resend
        rr = requests.post(f"{API}/auth/resend-verification", json={"email": email}, timeout=20)
        assert rr.status_code == 200
        assert rr.json().get("already_verified") is True

    def test_admin_login_still_works_without_re_verification(self, admin_session):
        # Fixture already logs in successfully; assert /me returns admin
        me = admin_session.get(f"{API}/auth/me", timeout=20)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == ADMIN_EMAIL
        assert me.json()["user"].get("email_verified") is True


# ---------------- Healing Parks (Geolocation) ----------------
class TestHealingParksGeo:
    """Verify haversine distance sorting."""

    def test_parks_with_geolocation_sorted_by_distance(self):
        # Coordinates of Taman Suropati exactly: -6.2008, 106.8333 -> distance ~0km
        r = requests.get(f"{API}/healing/parks", params={"lat": -6.2008, "lng": 106.8333}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data["items"]
        assert len(items) >= 3
        assert data["user_lat"] == -6.2008
        assert data["user_lng"] == 106.8333
        # All items should have distance_km
        for it in items:
            assert "distance_km" in it
            assert isinstance(it["distance_km"], (int, float))
        # Closest should be Taman Suropati at ~0km
        assert items[0]["place_id"] == "taman_suropati", f"expected taman_suropati first, got {items[0]['place_id']}"
        assert items[0]["distance_km"] == 0.0 or items[0]["distance_km"] < 0.01
        # Sorted ascending
        distances = [it["distance_km"] for it in items]
        assert distances == sorted(distances), f"items not sorted by distance: {distances}"

    def test_parks_without_geolocation_no_distance_km(self):
        r = requests.get(f"{API}/healing/parks", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["user_lat"] is None
        assert data["user_lng"] is None
        items = data["items"]
        assert len(items) >= 3
        for it in items:
            assert "distance_km" not in it, f"distance_km should not be set without geo: {it}"


# ---------------- WebSocket Chat ----------------
class TestWebSocketChat:
    """Test /api/ws/chat/{booking_id} streaming chat."""

    @pytest.fixture(scope="class")
    def verified_user(self):
        """Register, verify, login, create booking. Returns dict with token, booking_id."""
        email = f"TEST_ws_{uuid.uuid4().hex[:8]}@example.com"
        pw = "Test@2026!"
        r = _register_user(email, password=pw)
        assert r.status_code == 200
        token = _extract_token_from_url(r.json()["dev_verification_url"])
        assert requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=20).status_code == 200

        s = requests.Session()
        lr = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
        assert lr.status_code == 200
        access_token = lr.json()["token"]

        # Create booking
        br = s.post(
            f"{API}/bookings",
            json={"doctor_id": "doc_elena_vance", "date": "2026-02-01", "time": "10:00 AM", "category": "anxiety", "note": "WS test"},
            timeout=20,
        )
        assert br.status_code == 200, br.text
        booking_id = br.json()["booking_id"]
        return {"access_token": access_token, "booking_id": booking_id, "email": email}

    @pytest.mark.asyncio
    async def test_websocket_no_auth_closes_1008(self, verified_user):
        url = f"{WS_BASE}/api/ws/chat/{verified_user['booking_id']}"
        # Connect without any auth -> should receive error and close
        try:
            async with websockets.connect(url, open_timeout=20) as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                assert data.get("type") == "error"
                # Wait for close
                try:
                    await asyncio.wait_for(ws.recv(), timeout=5)
                except websockets.ConnectionClosed as e:
                    assert e.code == 1008, f"expected close 1008, got {e.code}"
        except websockets.ConnectionClosed as e:
            # Some implementations close immediately
            assert e.code == 1008

    @pytest.mark.asyncio
    async def test_websocket_wrong_booking_id_closes(self, verified_user):
        url = f"{WS_BASE}/api/ws/chat/bk_nonexistent_xxx?token={verified_user['access_token']}"
        try:
            async with websockets.connect(url, open_timeout=20) as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                assert data.get("type") == "error"
                assert "booking" in data.get("message", "").lower() or "not found" in data.get("message", "").lower()
        except websockets.ConnectionClosed as e:
            assert e.code == 1008

    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, verified_user):
        url = f"{WS_BASE}/api/ws/chat/{verified_user['booking_id']}?token={verified_user['access_token']}"
        async with websockets.connect(url, open_timeout=20) as ws:
            # Expect ready
            ready = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            assert ready.get("type") == "ready"
            assert ready.get("booking_id") == verified_user["booking_id"]

            # Ping
            await ws.send(json.dumps({"type": "ping"}))
            pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            assert pong.get("type") == "pong"

    @pytest.mark.asyncio
    async def test_websocket_streaming_ai_response(self, verified_user):
        url = f"{WS_BASE}/api/ws/chat/{verified_user['booking_id']}?token={verified_user['access_token']}"
        async with websockets.connect(url, open_timeout=20) as ws:
            ready = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            assert ready.get("type") == "ready"

            # Send user message
            await ws.send(json.dumps({"type": "user_message", "content": "Halo dok, saya merasa sedikit cemas hari ini."}))

            got_user_message = False
            got_typing = False
            chunks = []
            ai_message = None
            # Read events with overall timeout ~60s for Claude
            deadline = time.time() + 60
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=45)
                except asyncio.TimeoutError:
                    break
                evt = json.loads(raw)
                etype = evt.get("type")
                if etype == "user_message":
                    got_user_message = True
                    assert evt["message"]["role"] == "user"
                    assert "cemas" in evt["message"]["content"].lower()
                elif etype == "typing":
                    got_typing = True
                elif etype == "ai_chunk":
                    chunks.append(evt)
                    assert "delta" in evt
                    assert "content_so_far" in evt
                    assert "message_id" in evt
                elif etype == "ai_message":
                    ai_message = evt["message"]
                    break
                elif etype == "error":
                    pytest.fail(f"WS error event: {evt}")

            assert got_user_message, "user_message event not received"
            assert got_typing, "typing event not received"
            assert len(chunks) > 0, "no ai_chunk events received"
            assert ai_message is not None, "ai_message event not received"
            assert ai_message["role"] == "assistant"
            assert len(ai_message["content"]) > 0
            # Verify chunks accumulate to full content
            final_so_far = chunks[-1]["content_so_far"]
            assert final_so_far == ai_message["content"], (
                f"final chunk content_so_far does not equal ai_message.content; "
                f"chunk_len={len(final_so_far)}, ai_len={len(ai_message['content'])}"
            )
            # All chunks share same message_id
            assert all(c["message_id"] == ai_message["message_id"] for c in chunks)
