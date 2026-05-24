from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

import bcrypt
import jwt
import requests
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
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
                    "avatar_url": "https://static.prod-images.emergentagent.com/jobs/7fb04be7-ed7d-415a-b6ee-6f602642e7b9/images/cae4a84b4f820dfffa26e94765de3c6b836dda3ec59cffca36818667d4582b00.png",
                    "settings": {},
                    "created_at": now_utc().isoformat(),
                }
            )

    # Seed doctors
    for d in DOCTORS_SEED:
        await db.doctors.update_one({"doctor_id": d["doctor_id"]}, {"$set": d}, upsert=True)
    for p in PARKS_SEED:
        await db.parks.update_one({"place_id": p["place_id"]}, {"$set": p}, upsert=True)
    for m in MEDITATIONS_SEED:
        await db.meditations.update_one({"meditation_id": m["meditation_id"]}, {"$set": m}, upsert=True)


# ---------------------- Auth ----------------------
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
    token = create_access_token(user_id, email)
    set_auth_cookie(response, token)
    return {"user": serialize({**user}), "token": token}


@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau password salah")
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
async def list_parks(mood: Optional[str] = None):
    cursor = db.parks.find({}, {"_id": 0})
    items = await cursor.to_list(50)
    return {"items": items, "mood_hint": mood or "anxious"}


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
