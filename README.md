# Sears Home Services — Voice AI Agent

An inbound voice AI agent that troubleshoots home appliances, schedules technician visits, and optionally captures appliance photos for visual diagnosis.

## Live Demo

**Call now:** `+1 (662) 591-9049`

Alex answers immediately, 24/7. No waiting, no "press 1 for…".

## Quick Start

### Prerequisites

- Docker + Docker Compose
- ngrok (for local Twilio webhook exposure)

### 1. Clone and configure

```bash
cp .env.example .env
# Fill in your API keys (see API Keys section below)
```

### 2. Start the stack

```bash
docker compose up --build
```

This starts PostgreSQL and the FastAPI app on port 8000. The database is seeded automatically with 10 sample technicians.

### 3. Expose publicly for Twilio

```bash
ngrok http 8000
```

Copy the `https://` URL ngrok gives you and set `BASE_URL` in `.env` to that value, then restart:

```bash
docker compose up --build -d
```

### 4. Configure Twilio

In your [Twilio Console](https://console.twilio.com), go to your phone number's settings and set the **Voice webhook** (HTTP POST) to:

```
https://<your-ngrok-url>/inbound
```

### 5. Call your number

Call your Twilio phone number. Alex will answer within 2-3 seconds.

---

## Testing Without a Phone Call

Use the included `chat.py` script to talk to the agent directly in your terminal — no Twilio, no Deepgram, no cost:

```bash
python chat.py
```

This runs the full GPT-4o conversation loop with real database queries. Good for testing scheduling, tool calls, and conversation flow.

---

## Running Tests

```bash
pytest tests/ -v
```

38 tests, no external services required (OpenAI/Deepgram/Resend are mocked, SQLite used instead of PostgreSQL).

---

## API Keys Required

| Service | Purpose | Get It |
|---|---|---|
| [Twilio](https://twilio.com) | Inbound calls + Media Streams | Free trial ($15 credit) |
| [OpenAI](https://platform.openai.com) | GPT-4o (LLM + Vision) + TTS | Pay-per-use |
| [Deepgram](https://deepgram.com) | Real-time speech-to-text | 200 hrs/month free |
| [Resend](https://resend.com) | Email for image upload links | 3,000 emails/month free |

---

## Architecture

```
Caller
  → Twilio (phone number)
  → POST /inbound → FastAPI returns TwiML opening a WebSocket
  ↕ WebSocket /stream (bidirectional audio)
      → Deepgram Nova-2 (real-time STT, ~200ms latency)
      → GPT-4o (conversation + tool calls for scheduling/vision)
      → OpenAI TTS → mulaw 8kHz audio → back to caller
```

**Barge-in:** When the caller speaks mid-response, the agent stops immediately — Twilio's audio buffer is cleared and queued responses are discarded.

**Tier 3 visual flow (side-channel):**
```
Agent requests email → Resend sends /upload/{token} link
Caller uploads photo → GPT-4o Vision analyzes it
Result fed back into conversation via get_image_analysis tool call
```

See `docs/design.md` for full architectural details and design decisions.

---

## Live Deployment (Railway)

1. Push to a GitHub repo
2. Create a new [Railway](https://railway.app) project → "Deploy from GitHub repo"
3. Add environment variables from `.env`
4. Railway assigns a public HTTPS URL — set that as `BASE_URL` in Railway env vars
5. Update your Twilio webhook to the Railway URL

---

## Project Structure

```
app/
  agent/          conversation loop, prompts, tools, TTS, audio conversion
  telephony/      Twilio webhook + WebSocket stream handler
  scheduling/     ORM models, queries, seed data
  vision/         image upload, email sender, GPT-4o Vision analyzer
  config.py       pydantic-settings (loads .env)
  db.py           SQLAlchemy engine, session factory
  main.py         FastAPI app, router wiring, lifespan
tests/            38 unit tests (SQLite, mocked external services)
chat.py           local chat test — talk to the agent without calling
docs/design.md    Technical design document
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key (GPT-4o + TTS) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `TWILIO_ACCOUNT_SID` | For live calls | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | For live calls | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | For live calls | Your Twilio number |
| `DEEPGRAM_API_KEY` | For live calls | Deepgram API key |
| `RESEND_API_KEY` | For Tier 3 | Resend API key |
| `BASE_URL` | Yes | Public URL (ngrok or Railway) |
