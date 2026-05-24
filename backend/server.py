from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
import secrets
import asyncio
import math
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal, Dict

import bcrypt
import jwt
import requests
import resend
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai import OpenAISpeechToText
import io

# ---------------------- App / DB Setup ----------------------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

app = FastAPI(title="EchoAid API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echoaid")


# ---------------------- Helpers ----------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": now_utc() + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def set_session_cookie(response: Response, session_token: str):
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _verification_email_html(name: str, link: str) -> str:
    return f"""
    <!doctype html>
    <html><body style="margin:0;padding:0;background:#F4F7F4;font-family:Arial,Helvetica,sans-serif;color:#1C302B;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="padding:40px 16px;">
        <table width="560" cellpadding="0" cellspacing="0" border="0" style="background:#FFFFFF;border-radius:24px;overflow:hidden;box-shadow:0 8px 32px rgba(45,95,95,0.08);">
          <tr><td style="background:#2D5F5F;padding:28px 32px;color:#FFFFFF;">
            <div style="font-size:11px;letter-spacing:3px;text-transform:uppercase;opacity:0.7;">EchoAid Sanctuary</div>
            <div style="font-size:24px;font-weight:600;margin-top:4px;">Selamat datang, {name}!</div>
          </td></tr>
          <tr><td style="padding:32px;">
            <p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#1C302B;">
              Terima kasih sudah bergabung dengan <strong>EchoAid</strong> — sanctuary digital untuk kesehatan mental kamu.
            </p>
            <p style="margin:0 0 22px;font-size:15px;line-height:1.7;color:#4A635D;">
              Klik tombol di bawah untuk memverifikasi email kamu. Link ini berlaku selama 24 jam.
            </p>
            <table cellpadding="0" cellspacing="0" border="0"><tr><td align="center" bgcolor="#2D5F5F" style="border-radius:999px;">
              <a href="{link}" style="display:inline-block;padding:14px 28px;font-size:14px;font-weight:600;color:#FFFFFF;text-decoration:none;">Verifikasi Email Saya</a>
            </td></tr></table>
            <p style="margin:24px 0 0;font-size:12px;line-height:1.6;color:#7A9690;">
              Jika tombol tidak bekerja, salin link ini: <br/>
              <span style="word-break:break-all;color:#2D5F5F;">{link}</span>
            </p>
          </td></tr>
          <tr><td style="padding:18px 32px;background:#F4F7F4;color:#7A9690;font-size:11px;">
            Kamu menerima email ini karena baru saja mendaftar di EchoAid. Jika ini bukan kamu, abaikan saja email ini.
          </td></tr>
        </table>
      </td></tr></table>
    </body></html>
    """


async def send_verification_email(to_email: str, name: str, token: str) -> Dict[str, Optional[str]]:
    """Returns dict with email_id and optional dev_link (when send failed in testing mode)."""
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    is_testing = SENDER_EMAIL.endswith("@resend.dev")
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email send")
        logger.info(f"[DEV] Verification link for {to_email}: {link}")
        return {"email_id": None, "dev_link": link if is_testing else None}
    params = {
        "from": f"EchoAid Sanctuary <{SENDER_EMAIL}>",
        "to": [to_email],
        "subject": "Verifikasi email kamu untuk EchoAid Sanctuary",
        "html": _verification_email_html(name, link),
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        email_id = result.get("id") if isinstance(result, dict) else None
        return {"email_id": email_id, "dev_link": None}
    except Exception as e:
        logger.exception(f"Failed to send verification email: {e}")
        # Log link to console as fallback
        logger.info(f"[FALLBACK] Verification link for {to_email}: {link}")
        # In testing mode, surface dev link so the demo works without verified domain
        return {"email_id": None, "dev_link": link if is_testing else None}


def serialize(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


async def get_user_by_token(token: str) -> Optional[dict]:
    """Resolve JWT or Emergent session_token to a user document."""
    if not token:
        return None
    # Try JWT first
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        uid = payload.get("sub")
        if uid:
            user = await db.users.find_one({"user_id": uid}, {"_id": 0})
            if user:
                user.pop("password_hash", None)
                return user
    except jwt.PyJWTError:
        pass
    # Try Emergent session_token
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at >= now_utc():
            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
            if user:
                user.pop("password_hash", None)
                return user
    return None


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token") or request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    user = await get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ---------------------- Pydantic Models ----------------------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    nickname: Optional[str] = ""
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    university: Optional[str] = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MoodIn(BaseModel):
    mood: Literal["grateful", "calm", "neutral", "low", "anxious"]
    note: Optional[str] = ""


class JournalIn(BaseModel):
    mode: Literal["text", "voice"] = "text"
    content: str
    mood: Optional[str] = None


class BookingIn(BaseModel):
    doctor_id: str
    date: str  # ISO date "YYYY-MM-DD"
    time: str  # "10:00 AM"
    category: Optional[str] = None
    note: Optional[str] = ""


class ChatIn(BaseModel):
    booking_id: str
    message: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    university: Optional[str] = None
    avatar_url: Optional[str] = None
    sanctuary_preferences: Optional[dict] = None
    daily_support_routine: Optional[list] = None
    privacy: Optional[dict] = None
    guardian_circle: Optional[list] = None


class SettingsUpdate(BaseModel):
    notifications: Optional[bool] = None
    weekly_wellness_report: Optional[bool] = None
    consultation_reminders: Optional[bool] = None
    community_updates: Optional[bool] = None
    mood_check_in_alert: Optional[bool] = None
    reduce_motion: Optional[bool] = None
    larger_text: Optional[bool] = None
    dark_mode: Optional[bool] = None


# ---------------------- Static seed data ----------------------
DOCTORS_SEED = [
    {
        "doctor_id": "doc_elena_vance",
        "name": "Dr. Elena Vance",
        "title": "Clinical Psychologist",
        "rating": 4.9,
        "specialties": ["Anxiety", "CBT", "Academic Pressure"],
        "categories": ["anxiety", "academic_stress"],
        "image": "https://images.unsplash.com/photo-1650728287460-37c20c1c6a30?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjV8MHwxfHNlYXJjaHwyfHxmcmllbmRseSUyMHBzeWNob2xvZ2lzdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc3OTYxNzg1NXww&ixlib=rb-4.1.0&q=85",
        "bio": "Specializes in Cognitive Behavioural Therapy for students experiencing academic burnout and anxiety.",
        "next_available": "Tomorrow, 10:00 AM",
    },
    {
        "doctor_id": "doc_julian_thorne",
        "name": "Dr. Julian Thorne",
        "title": "Behavioral Specialist",
        "rating": 4.8,
        "specialties": ["Relationships", "Self-Esteem"],
        "categories": ["relationships", "depression"],
        "image": "https://images.pexels.com/photos/3958409/pexels-photo-3958409.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "bio": "Membantu klien membangun pola pikir sehat di lingkungan sosial dan profesional.",
        "next_available": "Today, 4:30 PM",
    },
    {
        "doctor_id": "doc_nadia_kusuma",
        "name": "Dr. Nadia Kusuma",
        "title": "Trauma & Mindfulness Therapist",
        "rating": 4.9,
        "specialties": ["Trauma", "Mindfulness", "Stress"],
        "categories": ["trauma", "anxiety"],
        "image": "https://images.pexels.com/photos/6712647/pexels-photo-6712647.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "bio": "Berpengalaman dalam trauma-informed therapy dan mindfulness berbasis bukti WHO LIVE LIFE.",
        "next_available": "Friday, 2:30 PM",
    },
]

PARKS_SEED = [
    {
        "place_id": "taman_menteng",
        "name": "Taman Menteng",
        "subtitle": "Quiet Zone - Peaceful Garden",
        "tags": ["Nature", "Secluded"],
        "lat": -6.1959,
        "lng": 106.8324,
        "distance": "400m away",
        "image": "https://images.unsplash.com/photo-1613370625437-f2956da172ef?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NjV8MHwxfHNlYXJjaHwyfHxwZWFjZWZ1bCUyMHVyYmFuJTIwcGFyayUyMG5hdHVyZXxlbnwwfHx8fDE3Nzk2MTc4NTV8MA&ixlib=rb-4.1.0&q=85",
    },
    {
        "place_id": "taman_suropati",
        "name": "Taman Suropati",
        "subtitle": "Peaceful Garden",
        "tags": ["Nature", "Physical"],
        "lat": -6.2008,
        "lng": 106.8333,
        "distance": "1.2km away",
        "image": "https://images.pexels.com/photos/16605520/pexels-photo-16605520.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    },
    {
        "place_id": "lapangan_banteng",
        "name": "Lapangan Banteng",
        "subtitle": "Open Sky - Grounding Walk",
        "tags": ["Open Space", "Physical"],
        "lat": -6.1700,
        "lng": 106.8350,
        "distance": "2.5km away",
        "image": "https://images.pexels.com/photos/16605520/pexels-photo-16605520.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    },
]

MEDITATIONS_SEED = [
    {
        "meditation_id": "med_478",
        "title": "Mastering the 4-7-8 Breathing Method",
        "subtitle": "A simple, evidence-based technique to quiet your nervous system during high-stress academic periods.",
        "duration_min": 5,
        "category": "Breathwork",
        "image": "https://static.prod-images.emergentagent.com/jobs/7fb04be7-ed7d-415a-b6ee-6f602642e7b9/images/ad44a9a2c8ec2da2954b8b4a36af3f30d82378981d46b583ba43605b2cf79139.png",
        "steps": [
            "Duduk tegak, lepaskan beban di bahu.",
            "Tarik napas perlahan melalui hidung selama 4 detik.",
            "Tahan napas selama 7 detik.",
            "Hembuskan perlahan melalui mulut selama 8 detik.",
            "Ulangi 4 siklus.",
        ],
    },
    {
        "meditation_id": "med_grounding",
        "title": "5-4-3-2-1 Grounding for Anxious Minds",
        "subtitle": "Bring yourself back to the present moment using your five senses.",
        "duration_min": 4,
        "category": "Grounding",
        "image": "https://images.unsplash.com/photo-1613370625437-f2956da172ef?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NjV8MHwxfHNlYXJjaHwyfHxwZWFjZWZ1bCUyMHVyYmFuJTIwcGFyayUyMG5hdHVyZXxlbnwwfHx8fDE3Nzk2MTc4NTV8MA&ixlib=rb-4.1.0&q=85",
        "steps": [
            "Sebutkan 5 hal yang kamu lihat.",
            "Sebutkan 4 hal yang bisa kamu sentuh.",
            "Sebutkan 3 suara yang kamu dengar.",
            "Sebutkan 2 aroma di sekitarmu.",
            "Sebutkan 1 rasa di mulutmu.",
        ],
    },
    {
        "meditation_id": "med_body_scan",
        "title": "10-Minute Body Scan Relaxation",
        "subtitle": "Release tension built up from long study sessions.",
        "duration_min": 10,
        "category": "Body Scan",
        "image": "https://images.pexels.com/photos/16605520/pexels-photo-16605520.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "steps": [
            "Berbaring nyaman, tutup mata.",
            "Fokus pada ujung kaki, lepaskan ketegangan.",
            "Perlahan naik ke betis, paha, perut, dada.",
            "Rasakan leher, rahang, dan dahi melembut.",
            "Akhiri dengan tiga napas dalam.",
        ],
    },
]


# ---------------------- Startup ----------------------
@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.mood_entries.create_index([("user_id", 1), ("created_at", -1)])
    await db.journal_entries.create_index([("user_id", 1), ("created_at", -1)])
    await db.bookings.create_index([("user_id", 1), ("status", 1)])
    await db.chat_messages.create_index([("booking_id", 1), ("created_at", 1)])

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_password:
        existing = await db.users.find_one({"email": admin_email.lower()})
        if not existing:
            await db.users.insert_one(
                {
                    "user_id": f"user_{uuid.uuid4().hex[:12]}",
                    "email": admin_email.lower(),
                    "name": "EchoAid Admin",
                    "nickname": "Admin",
                    "university": "EchoAid HQ",
                    "role": "admin",
                    "password_hash": hash_password(admin_password),
                    "auth_provider": "password",
                    "email_verified": True,
                    "avatar_url": "https://static.prod-images.emergentagent.com/jobs/7fb04be7-ed7d-415a-b6ee-6f602642e7b9/images/cae4a84b4f820dfffa26e94765de3c6b836dda3ec59cffca36818667d4582b00.png",
                    "settings": {},
                    "created_at": now_utc().isoformat(),
                }
            )

    # Ensure existing admin has email_verified=True (backfill)
    if admin_email:
        await db.users.update_one(
            {"email": admin_email.lower()},
            {"$set": {"email_verified": True}},
        )

    await db.email_verification_tokens.create_index("token", unique=True)

    # Seed doctors
    for d in DOCTORS_SEED:
        await db.doctors.update_one({"doctor_id": d["doctor_id"]}, {"$set": d}, upsert=True)
    for p in PARKS_SEED:
        await db.parks.update_one({"place_id": p["place_id"]}, {"$set": p}, upsert=True)
    for m in MEDITATIONS_SEED:
        await db.meditations.update_one({"meditation_id": m["meditation_id"]}, {"$set": m}, upsert=True)


# ---------------------- Auth ----------------------
async def _issue_verification_token(user_id: str, email: str, name: str):
    token = secrets.token_urlsafe(32)
    expires_at = (now_utc() + timedelta(hours=24)).isoformat()
    await db.email_verification_tokens.insert_one({
        "token": token,
        "user_id": user_id,
        "email": email,
        "expires_at": expires_at,
        "created_at": now_utc().isoformat(),
        "used": False,
    })
    send_result = await send_verification_email(email, name, token)
    return token, send_result


@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user = {
        "user_id": user_id,
        "email": email,
        "name": body.name,
        "nickname": body.nickname or body.name.split(" ")[0],
        "university": body.university or "",
        "role": "user",
        "password_hash": hash_password(body.password),
        "auth_provider": "password",
        "email_verified": False,
        "avatar_url": "https://static.prod-images.emergentagent.com/jobs/7fb04be7-ed7d-415a-b6ee-6f602642e7b9/images/cae4a84b4f820dfffa26e94765de3c6b836dda3ec59cffca36818667d4582b00.png",
        "sanctuary_preferences": {"dark_mode": False, "daily_reminders": True},
        "daily_support_routine": [
            {"id": "morning", "title": "Morning Vitality", "schedule": "07:00 AM", "status": "active"},
            {"id": "sleep", "title": "Restful Sleep Aid", "schedule": "10:30 PM", "status": "upcoming"},
        ],
        "privacy": {"biometric_lock": False, "journal_encryption": True},
        "guardian_circle": [],
        "settings": {
            "notifications": True,
            "weekly_wellness_report": True,
            "consultation_reminders": True,
            "community_updates": False,
            "mood_check_in_alert": True,
            "reduce_motion": False,
            "larger_text": False,
            "dark_mode": False,
        },
        "created_at": now_utc().isoformat(),
    }
    await db.users.insert_one(user)
    # Issue verification token + send email (do NOT log in)
    _, send_result = await _issue_verification_token(user_id, email, body.name)
    payload = {
        "ok": True,
        "email": email,
        "message": "Akun berhasil dibuat. Cek email kamu untuk verifikasi.",
        "email_verified": False,
    }
    # In testing mode (no verified Resend domain), expose dev link so demo flows complete
    if send_result.get("dev_link"):
        payload["dev_verification_url"] = send_result["dev_link"]
        payload["dev_mode_note"] = (
            "Mode testing: Resend hanya mengirim email ke alamat terverifikasi. "
            "Untuk demo, gunakan link di dev_verification_url. Verifikasi domain di resend.com/domains untuk produksi."
        )
    return payload


@api.post("/auth/verify-email")
async def verify_email(request: Request):
    body = await request.json()
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token tidak valid")
    doc = await db.email_verification_tokens.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=400, detail="Token tidak ditemukan atau sudah digunakan")
    if doc.get("used"):
        raise HTTPException(status_code=400, detail="Token sudah digunakan. Silakan login.")
    expires_at = doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now_utc():
        raise HTTPException(status_code=400, detail="Token kadaluarsa. Minta link verifikasi baru.")
    await db.users.update_one({"user_id": doc["user_id"]}, {"$set": {"email_verified": True}})
    await db.email_verification_tokens.update_one({"token": token}, {"$set": {"used": True, "used_at": now_utc().isoformat()}})
    return {"ok": True, "email": doc["email"]}


@api.post("/auth/resend-verification")
async def resend_verification(request: Request):
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email wajib diisi")
    user = await db.users.find_one({"email": email})
    if not user:
        # Don't leak existence
        return {"ok": True}
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    # Invalidate previous tokens for this user
    await db.email_verification_tokens.update_many({"user_id": user["user_id"], "used": False}, {"$set": {"used": True}})
    _, send_result = await _issue_verification_token(user["user_id"], email, user.get("name", "Sanctuary Member"))
    payload = {"ok": True}
    if send_result.get("dev_link"):
        payload["dev_verification_url"] = send_result["dev_link"]
    return payload


@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    if user.get("email_verified") is False:
        # Block login until email is verified
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": "Email belum diverifikasi. Cek inbox kamu atau kirim ulang link verifikasi.",
                "email": email,
            },
        )
    token = create_access_token(user["user_id"], email)
    set_auth_cookie(response, token)
    return {"user": serialize(user), "token": token}


@api.post("/auth/google-session")
async def google_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    # Call Emergent Auth service
    try:
        r = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to verify session: {e}")

    email = data["email"].lower()
    name = data.get("name", "")
    picture = data.get("picture", "")
    session_token = data["session_token"]

    existing = await db.users.find_one({"email": email})
    if not existing:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "nickname": name.split(" ")[0] if name else email.split("@")[0],
            "university": "",
            "role": "user",
            "auth_provider": "google",
            "email_verified": True,
            "avatar_url": picture or "https://static.prod-images.emergentagent.com/jobs/7fb04be7-ed7d-415a-b6ee-6f602642e7b9/images/cae4a84b4f820dfffa26e94765de3c6b836dda3ec59cffca36818667d4582b00.png",
            "sanctuary_preferences": {"dark_mode": False, "daily_reminders": True},
            "daily_support_routine": [
                {"id": "morning", "title": "Morning Vitality", "schedule": "07:00 AM", "status": "active"},
                {"id": "sleep", "title": "Restful Sleep Aid", "schedule": "10:30 PM", "status": "upcoming"},
            ],
            "privacy": {"biometric_lock": False, "journal_encryption": True},
            "guardian_circle": [],
            "settings": {
                "notifications": True,
                "weekly_wellness_report": True,
                "consultation_reminders": True,
                "community_updates": False,
                "mood_check_in_alert": True,
                "reduce_motion": False,
                "larger_text": False,
                "dark_mode": False,
            },
            "created_at": now_utc().isoformat(),
        }
        await db.users.insert_one(user)
    else:
        user_id = existing["user_id"]

    # Store session
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {
            "$set": {
                "session_token": session_token,
                "user_id": user_id,
                "expires_at": (now_utc() + timedelta(days=7)).isoformat(),
                "created_at": now_utc().isoformat(),
            }
        },
        upsert=True,
    )
    set_session_cookie(response, session_token)
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"user": user_doc}


@api.post("/auth/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}


# ---------------------- Mood ----------------------
@api.post("/mood")
async def create_mood(body: MoodIn, user: dict = Depends(get_current_user)):
    entry = {
        "entry_id": f"mood_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "mood": body.mood,
        "note": body.note or "",
        "created_at": now_utc().isoformat(),
    }
    await db.mood_entries.insert_one(entry.copy())
    entry.pop("_id", None)
    return entry


@api.get("/mood")
async def list_moods(user: dict = Depends(get_current_user)):
    cursor = db.mood_entries.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(60)
    items = await cursor.to_list(60)
    return {"items": items}


# ---------------------- Journal ----------------------
@api.post("/journal")
async def create_journal(body: JournalIn, user: dict = Depends(get_current_user)):
    entry = {
        "entry_id": f"jrn_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "mode": body.mode,
        "content": body.content,
        "mood": body.mood,
        "created_at": now_utc().isoformat(),
    }
    await db.journal_entries.insert_one(entry.copy())
    entry.pop("_id", None)
    return entry


@api.get("/journal")
async def list_journal(user: dict = Depends(get_current_user)):
    cursor = db.journal_entries.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(50)
    items = await cursor.to_list(50)
    return {"items": items}


@api.post("/journal/transcribe")
async def transcribe_journal(
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    data = await audio.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio too large (max 25MB)")
    stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
    buf = io.BytesIO(data)
    # The library expects a file-like object with a name attribute
    buf.name = audio.filename or "voice.webm"
    try:
        response = await stt.transcribe(file=buf, model="whisper-1", response_format="json")
        text = getattr(response, "text", None) or (response.get("text") if isinstance(response, dict) else "")
    except Exception as e:
        logger.exception("Whisper transcribe failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    return {"text": text or ""}


# ---------------------- Healing Map ----------------------
@api.get("/healing/parks")
async def list_parks(mood: Optional[str] = None, lat: Optional[float] = None, lng: Optional[float] = None):
    cursor = db.parks.find({}, {"_id": 0})
    items = await cursor.to_list(50)
    # If user shared geolocation, compute distances + sort
    if lat is not None and lng is not None:
        for it in items:
            d = haversine_km(lat, lng, it.get("lat"), it.get("lng"))
            it["distance_km"] = round(d, 2)
            it["distance"] = f"{int(d * 1000)}m away" if d < 1 else f"{d:.1f}km away"
        items.sort(key=lambda x: x.get("distance_km", 9999))
    return {"items": items, "mood_hint": mood or "anxious", "user_lat": lat, "user_lng": lng}


# ---------------------- Meditation ----------------------
@api.get("/meditations")
async def list_meditations():
    cursor = db.meditations.find({}, {"_id": 0})
    items = await cursor.to_list(50)
    return {"items": items}


@api.get("/meditations/{meditation_id}")
async def get_meditation(meditation_id: str):
    item = await db.meditations.find_one({"meditation_id": meditation_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Meditation not found")
    return item


# ---------------------- Consultation / Booking ----------------------
@api.get("/doctors")
async def list_doctors(category: Optional[str] = None, q: Optional[str] = None):
    query = {}
    if category:
        query["categories"] = category
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"specialties": {"$regex": q, "$options": "i"}},
            {"title": {"$regex": q, "$options": "i"}},
        ]
    cursor = db.doctors.find(query, {"_id": 0})
    items = await cursor.to_list(50)
    return {"items": items}


@api.post("/bookings")
async def create_booking(body: BookingIn, user: dict = Depends(get_current_user)):
    doctor = await db.doctors.find_one({"doctor_id": body.doctor_id}, {"_id": 0})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    booking_id = f"bk_{uuid.uuid4().hex[:12]}"
    booking = {
        "booking_id": booking_id,
        "user_id": user["user_id"],
        "doctor_id": body.doctor_id,
        "doctor_name": doctor["name"],
        "doctor_title": doctor["title"],
        "doctor_image": doctor["image"],
        "date": body.date,
        "time": body.time,
        "category": body.category or "",
        "note": body.note or "",
        "status": "confirmed",
        "created_at": now_utc().isoformat(),
    }
    await db.bookings.insert_one(booking.copy())
    booking.pop("_id", None)
    return booking


@api.get("/bookings")
async def list_bookings(user: dict = Depends(get_current_user)):
    cursor = db.bookings.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(50)
    return {"items": items}


# ---------------------- EchoChat (AI Doctor) ----------------------
def _doctor_system_prompt(doctor_name: str, doctor_title: str, user_name: str) -> str:
    return (
        f"Kamu adalah {doctor_name}, seorang {doctor_title} bersertifikat di platform EchoAid. "
        f"Kamu berbicara dengan klienmu, {user_name}, seorang mahasiswa atau pekerja muda (18-24) di Indonesia. "
        "Gaya bicara: empatik, hangat, mendukung, profesional, dan tidak menghakimi. "
        "Gunakan campuran Bahasa Indonesia dan English yang natural (seperti percakapan mahasiswa urban). "
        "Selalu validasi perasaan klien terlebih dulu, baru tawarkan teknik berbasis bukti "
        "(CBT, grounding 5-4-3-2-1, 4-7-8 breathing, journaling, behavioural activation) "
        "yang sejalan dengan kerangka WHO LIVE LIFE untuk pencegahan dan dukungan kesehatan mental. "
        "Hindari memberikan diagnosis klinis pasti. Jika klien menunjukkan tanda krisis atau bahaya diri, "
        "dengan lembut sarankan menghubungi layanan darurat lokal (119 ext 8 di Indonesia) atau kontak Guardian Circle mereka. "
        "Balasan singkat, hangat, satu atau dua paragraf, gunakan nama klien sesekali."
    )


@api.post("/chat/send")
async def chat_send(body: ChatIn, user: dict = Depends(get_current_user)):
    booking = await db.bookings.find_one({"booking_id": body.booking_id, "user_id": user["user_id"]}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=403, detail="Anda harus booking konsultasi terlebih dahulu untuk mengakses EchoChat")

    # Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    user_msg = {
        "message_id": user_msg_id,
        "booking_id": body.booking_id,
        "user_id": user["user_id"],
        "role": "user",
        "content": body.message,
        "created_at": now_utc().isoformat(),
    }
    await db.chat_messages.insert_one(user_msg.copy())

    # Build chat with Claude Sonnet 4.5
    system_prompt = _doctor_system_prompt(booking["doctor_name"], booking["doctor_title"], user.get("nickname") or user.get("name") or "teman")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=body.booking_id,
        system_message=system_prompt,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        ai_text = await chat.send_message(UserMessage(text=body.message))
    except Exception as e:
        logger.exception("Claude chat failed")
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")

    ai_msg = {
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "booking_id": body.booking_id,
        "user_id": user["user_id"],
        "role": "assistant",
        "content": ai_text,
        "doctor_name": booking["doctor_name"],
        "created_at": now_utc().isoformat(),
    }
    await db.chat_messages.insert_one(ai_msg.copy())
    user_msg.pop("_id", None)
    ai_msg.pop("_id", None)
    return {"user_message": user_msg, "ai_message": ai_msg}


@api.get("/chat/{booking_id}")
async def chat_history(booking_id: str, user: dict = Depends(get_current_user)):
    booking = await db.bookings.find_one({"booking_id": booking_id, "user_id": user["user_id"]}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=403, detail="Booking tidak ditemukan")
    cursor = db.chat_messages.find({"booking_id": booking_id, "user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1)
    items = await cursor.to_list(500)
    return {"booking": booking, "messages": items}


# ---------------------- WebSocket Chat ----------------------
@app.websocket("/api/ws/chat/{booking_id}")
async def ws_chat(websocket: WebSocket, booking_id: str):
    await websocket.accept()
    # Authenticate via cookie or query param token
    token = None
    cookie_header = websocket.headers.get("cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("access_token="):
            token = part[len("access_token="):]
            break
        if part.startswith("session_token="):
            token = part[len("session_token="):]
            break
    if not token:
        token = websocket.query_params.get("token")

    user = await get_user_by_token(token) if token else None
    if not user:
        await websocket.send_json({"type": "error", "message": "Not authenticated"})
        await websocket.close(code=1008)
        return

    booking = await db.bookings.find_one({"booking_id": booking_id, "user_id": user["user_id"]}, {"_id": 0})
    if not booking:
        await websocket.send_json({"type": "error", "message": "Booking not found"})
        await websocket.close(code=1008)
        return

    await websocket.send_json({"type": "ready", "booking_id": booking_id})

    # Per-connection chat session
    system_prompt = _doctor_system_prompt(
        booking["doctor_name"], booking["doctor_title"],
        user.get("nickname") or user.get("name") or "teman",
    )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=booking_id,
        system_message=system_prompt,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type != "user_message":
                continue
            text = (data.get("content") or "").strip()
            if not text:
                continue

            # Persist user message
            user_msg = {
                "message_id": f"msg_{uuid.uuid4().hex[:12]}",
                "booking_id": booking_id,
                "user_id": user["user_id"],
                "role": "user",
                "content": text,
                "created_at": now_utc().isoformat(),
            }
            await db.chat_messages.insert_one(user_msg.copy())
            user_msg.pop("_id", None)
            await websocket.send_json({"type": "user_message", "message": user_msg})

            # Typing indicator
            await websocket.send_json({"type": "typing", "doctor_name": booking["doctor_name"]})

            try:
                ai_text = await chat.send_message(UserMessage(text=text))
            except Exception as e:
                logger.exception("Claude chat failed in WS")
                await websocket.send_json({"type": "error", "message": "Pesan gagal diproses, coba lagi."})
                continue

            ai_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            ai_created = now_utc().isoformat()

            # Stream the response word by word (simulated streaming)
            words = ai_text.split(" ")
            buf = ""
            for i, w in enumerate(words):
                buf += (" " if i > 0 else "") + w
                await websocket.send_json({
                    "type": "ai_chunk",
                    "message_id": ai_msg_id,
                    "delta": (" " if i > 0 else "") + w,
                    "content_so_far": buf,
                })
                # Small delay for streaming effect (~30 wpm visual)
                await asyncio.sleep(0.03)

            ai_msg = {
                "message_id": ai_msg_id,
                "booking_id": booking_id,
                "user_id": user["user_id"],
                "role": "assistant",
                "content": ai_text,
                "doctor_name": booking["doctor_name"],
                "created_at": ai_created,
            }
            await db.chat_messages.insert_one(ai_msg.copy())
            ai_msg.pop("_id", None)
            await websocket.send_json({"type": "ai_message", "message": ai_msg})
    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------- Profile & Settings ----------------------
@api.patch("/profile")
async def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update:
        return {"user": user}
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"user": fresh}


@api.patch("/settings")
async def update_settings(body: SettingsUpdate, user: dict = Depends(get_current_user)):
    update = {f"settings.{k}": v for k, v in body.model_dump().items() if v is not None}
    if not update:
        return {"user": user}
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"user": fresh}


@api.post("/profile/guardian")
async def add_guardian(request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    guardian = {
        "guardian_id": f"g_{uuid.uuid4().hex[:8]}",
        "name": body.get("name", ""),
        "relation": body.get("relation", ""),
        "phone": body.get("phone", ""),
    }
    await db.users.update_one({"user_id": user["user_id"]}, {"$push": {"guardian_circle": guardian}})
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"user": fresh}


@api.delete("/profile/guardian/{guardian_id}")
async def remove_guardian(guardian_id: str, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$pull": {"guardian_circle": {"guardian_id": guardian_id}}},
    )
    fresh = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return {"user": fresh}


# ---------------------- Health ----------------------
@api.get("/")
async def root():
    return {"app": "EchoAid", "ok": True}


# ---------------------- Register routes ----------------------
app.include_router(api)

_frontend_url = os.environ.get("FRONTEND_URL", "")
_origins = os.environ.get("CORS_ORIGINS", "")
_origin_list = [o.strip() for o in _origins.split(",") if o.strip() and o.strip() != "*"]
if _frontend_url and _frontend_url not in _origin_list:
    _origin_list.append(_frontend_url)
# Always add localhost dev origins
for o in ["http://localhost:3000", "http://127.0.0.1:3000"]:
    if o not in _origin_list:
        _origin_list.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
