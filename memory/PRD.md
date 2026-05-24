# EchoAid — Product Requirements Document

## Problem Statement
EchoAid adalah platform kesehatan mental digital berbasis User-Centered Design untuk mahasiswa (18-24) dan pekerja muda di Indonesia.

## Architecture
- **Frontend**: React (CRA + craco) + Tailwind + Shadcn UI + Recharts + react-leaflet + lucide-react.
- **Backend**: FastAPI + Motor (MongoDB) + bcrypt + PyJWT + emergentintegrations + resend.
- **Auth**: JWT email/password (httpOnly cookie, email verification required) + Emergent Google OAuth (auto-verified).
- **LLMs (Emergent LLM Key)**: OpenAI Whisper for voice journal STT; Claude Sonnet 4.5 for EchoChat & Weekly Insights.
- **Email**: Resend (testing mode — dev_verification_url surfaced for demo flow).
- **Map**: Leaflet + OSM + browser geolocation + haversine sort.
- **Realtime**: FastAPI WebSocket at `/api/ws/chat/{booking_id}`.

## Implemented (Iteration 1 — 2026-02-24)
Login/Register, Home dashboard, Journal text+voice (Whisper), Healing Map, Meditation, Consultation booking, EchoChat (Claude), Profile, Settings, Support/SOS. Backend 27/27 tests.

## Implemented (Iteration 2 — 2026-02-24)
- Email verification flow via Resend.
- Geolocation-aware Healing Map (haversine sort).
- Real-time WebSocket chat (streaming Claude responses).
- Mobile portrait polish.
- Leaflet/OSM kept (Google Maps deferred).
- Backend 43/43 tests (16 new + 27 regression).

## Implemented (Iteration 3 — 2026-02-24)
- **Weekly AI Insights** on Home dashboard:
  - `GET /api/insights/weekly` — returns most-recent cached insight + 7-day stats + is_stale flag.
  - `POST /api/insights/weekly` — generates fresh Claude Sonnet 4.5 insight (Mood Pattern, Growth, Gentle Suggestion); 1-hour throttle to prevent abuse.
  - Aggregates: mood_counts, avg_mood_score, dominant_mood, journal_entries.
  - UI: sage-gradient card on Home with stats badge, "Generate Insight" button, animated refresh icon, staleness warning after 24h.
- **Backend hardening**: throttle 1/hour per user; sanitised error messages.
- Backend 52/52 tests (9 new + 43 regression).

## User Personas
- Mahasiswa 18-24 mengalami burnout akademis, kecemasan ujian.
- Pekerja muda terpapar stres pekerjaan, work-life balance.

## Prioritized Backlog (Post-Iter 3)
- **P0**: Resend domain verification (currently testing mode — only delivers to aelkurniawan13@gmail.com).
- **P1**: Google Maps API key + upgrade Healing Map.
- **P1**: Shareable Wellness Streak (anonymized weekly streak share badge).
- **P1**: Mood prediction (forecast next 3 days based on patterns).
- **P2**: PWA + offline-first journal.
- **P2**: Push notifications for daily reminders.
- **P2**: Community peer-support groups.
- **P2**: Split server.py (~1226 lines) into modular routers.
