# EchoAid — Product Requirements Document

## Problem Statement
EchoAid adalah platform kesehatan mental digital berbasis User-Centered Design untuk mahasiswa (18-24) dan pekerja muda di Indonesia.

## Architecture
- **Frontend**: React (CRA + craco) + Tailwind + Shadcn UI + Recharts + react-leaflet + lucide-react.
- **Backend**: FastAPI + Motor (MongoDB) + bcrypt + PyJWT + emergentintegrations + resend.
- **Auth**: JWT email/password (httpOnly cookie, email verification required) + Emergent Google OAuth (auto-verified).
- **LLMs (Emergent LLM Key)**: OpenAI Whisper for voice journal STT; Claude Sonnet 4.5 for EchoChat (streaming via WebSocket).
- **Email**: Resend (testing mode — sends only to verified address; dev_verification_url surfaced in API for demo flow).
- **Map**: Leaflet + OpenStreetMap; geolocation via browser API + haversine sort.
- **Realtime**: FastAPI WebSocket at `/api/ws/chat/{booking_id}` with simulated streaming.

## Implemented (Iteration 1 — 2026-02-24)
- Login/Register pages (email-password + Google OAuth).
- Sidebar dashboard layout.
- Home: mood check-in, daily quote, health correlation chart, healing map preview.
- Journal & MoodTracker: text + voice (Whisper) modes.
- Healing Map: parks list + Leaflet+OSM.
- Meditation: featured 4-7-8 + animated breathing player + library.
- Consultation: doctors list + filter + week-view calendar booking.
- EchoChat: Claude Sonnet 4.5 AI doctor — booking-gated.
- Profile: sanctuary preferences, daily routine, privacy, guardian circle.
- Settings: notifications, accessibility, account.
- Support/SOS page.
- 27/27 backend tests passed.

## Implemented (Iteration 2 — 2026-02-24)
- [x] **Email verification flow** via Resend (testing-mode aware with `dev_verification_url` in response for demo).
- [x] **Geolocation-aware Healing Map**: browser geolocation + haversine sort, real-time distance labels.
- [x] **Real-time WebSocket chat** at `/api/ws/chat/{booking_id}` with streaming AI response (token-by-token simulated, live/connecting/offline indicator).
- [x] **Mobile polish**: tighter mood grid on mobile, EchoChat mobile booking selector, sidebar hidden < md, bottom mobile nav.
- [x] **Leaflet/OSM** kept (Google Maps API key deferred until user obtains one).
- 43/43 backend tests passed (16 new + 27 regression).

## User Personas
- Mahasiswa 18-24 mengalami burnout akademis, kecemasan ujian, isolasi sosial.
- Pekerja muda terpapar stres pekerjaan, work-life balance.

## Prioritized Backlog (Post-Iter 2)
- **P0**: Verify Resend domain + change SENDER_EMAIL to noreply@echoaid.com (currently restricted to aelkurniawan13@gmail.com).
- **P1**: Mood AI insights from journal entries (Claude analyses).
- **P1**: Upgrade Healing Map to Google Maps (needs Maps JavaScript API key).
- **P1**: Shareable Wellness Streak feature (anonymized badge sharing).
- **P2**: PWA + offline first journal.
- **P2**: Push notifications for daily reminders.
- **P2**: Community peer-support groups.
