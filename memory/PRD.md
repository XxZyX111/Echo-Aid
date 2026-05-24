# EchoAid — Product Requirements Document

## Problem Statement
EchoAid adalah platform kesehatan mental digital berbasis User-Centered Design untuk mahasiswa (18-24) dan pekerja muda di Indonesia. Fitur inti: sign up/in dengan akun nyata, mood check-in dengan tracking, journal & voice-to-text (Whisper), Healing Map (Leaflet), Meditation, Consultation (booking dokter), EchoChat (AI doctor — Claude Sonnet 4.5 — hanya setelah booking), Profile, Settings, Support/SOS.

## Architecture
- **Frontend**: React (CRA + craco) + Tailwind + Shadcn UI + Recharts + react-leaflet + lucide-react.
- **Backend**: FastAPI + Motor (MongoDB) + bcrypt + PyJWT + emergentintegrations.
- **Auth**: JWT email/password (httpOnly cookie) + Emergent Google OAuth (session_token cookie).
- **LLMs (Emergent LLM Key)**: OpenAI Whisper (`whisper-1`) for voice journal STT; Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) for EchoChat.
- **Map**: Leaflet + OpenStreetMap (no API key required, free).
- **Color/Typography**: Sage green sanctuary palette (#2D5F5F primary, #E8F0EA secondary, #C06C5B accent). Outfit (headings) + Manrope (body).

## User Personas
- **Mahasiswa 18-24** mengalami burnout akademis, kecemasan ujian, isolasi sosial.
- **Pekerja muda** terpapar stres pekerjaan, work-life balance, hubungan profesional.

## Core Requirements (Done in 1st iteration)
- [x] Login/Register pages (email-password + Google).
- [x] Sidebar dashboard layout.
- [x] Home: greeting, daily quote, 5-emoji mood check-in, consultation CTA, health correlation chart, healing map preview.
- [x] Journal & MoodTracker: voice mode (Whisper transcription) + text mode, weekly growth panel, emotional landscape calendar, recent echoes.
- [x] Healing Map: nearby parks list + Leaflet map (Taman Menteng, Taman Suropati, Lapangan Banteng).
- [x] Meditation: featured 4-7-8 breathing guide with animated breathing player, library of guided exercises.
- [x] Consultation: doctors list (3 seeded), category filter, search, calendar week view + time slot booking.
- [x] EchoChat: AI doctor (Claude Sonnet 4.5) chat — only active after booking; multi-booking sidebar.
- [x] Profile: sanctuary preferences, daily support routine, privacy & security toggles, guardian circle CRUD, sign out.
- [x] Settings: notifications, accessibility, account management toggles.
- [x] Support/SOS page with emergency contacts.

## Implementation Date
- 2026-02-24 (Feb 2026): MVP completed and tested.

## Prioritized Backlog (Post-MVP)
- **P0**: Email verification flow for sign-up confirmation.
- **P0**: Mobile responsiveness polish (currently functional, can be refined for portrait phones).
- **P1**: Real-time chat with WebSocket fallback (currently polling-free request/response).
- **P1**: Mood prediction & AI insights from journal entries.
- **P1**: Geolocation API to detect user location & sort healing map by distance.
- **P2**: PWA support + offline first journal.
- **P2**: Push notifications for daily reminders.
- **P2**: Community peer-support groups.
