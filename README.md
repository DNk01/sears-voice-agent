# Sears Home Services — Voice AI Agent

An inbound voice AI agent that troubleshoots home appliances, schedules technician visits, and optionally captures appliance photos for visual diagnosis.

## Live Demo

**Call now:** `+1 (662) 591-9049`

Alex answers immediately, 24/7. No waiting, no "press 1 for…".

---

## Setup Guide

Follow these steps in order. Each step must be completed before moving to the next.

### Step 0 — Install required software

You need two programs installed on your computer before anything else:

**Docker Desktop**
1. Go to https://www.docker.com/products/docker-desktop
2. Download and install for your OS (Mac or Windows)
3. Open Docker Desktop and wait until it shows "Engine running"

**ngrok**
1. Go to https://ngrok.com and create a free account
2. Download ngrok for your OS
3. Run `ngrok config add-authtoken YOUR_TOKEN` (your token is shown on the ngrok dashboard after signup)

---

### Step 1 — Get your API keys

You need accounts on 4 services. All have free tiers.

| Service | Sign up | What you need |
|---|---|---|
| **Twilio** | https://twilio.com | Account SID, Auth Token, and a phone number (get one in Console → Phone Numbers → Buy) |
| **OpenAI** | https://platform.openai.com | API key (create at platform.openai.com/api-keys) — add $5 credit in Billing |
| **Deepgram** | https://deepgram.com | API key (create at console.deepgram.com) — free tier includes 200 hrs/month |
| **Resend** | https://resend.com | API key (create at resend.com/api-keys) — free tier, note: can only send to your own verified email address |

---

### Step 2 — Clone the project

```bash
git clone https://github.com/dnk01/sears-voice-agent
cd sears-voice-agent
```

---

### Step 3 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your keys:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx   ← from twilio.com/console
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx      ← from twilio.com/console
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx                       ← the number you bought in Twilio
OPENAI_API_KEY=sk-...                                  ← from platform.openai.com/api-keys
DEEPGRAM_API_KEY=...                                   ← from console.deepgram.com
RESEND_API_KEY=re_...                                  ← from resend.com/api-keys
DATABASE_URL=postgresql://sears:sears@db:5432/sears    ← leave this as-is
BASE_URL=                                              ← leave blank for now, fill in Step 5
```

---

### Step 4 — Start the application

```bash
docker compose up --build
```

Wait until you see this line — it means everything started correctly:
```
app-1  | INFO:     Application startup complete.
```

The database is automatically created and seeded with 10 sample technicians. Leave this terminal running.

---

### Step 5 — Expose your app to the internet

Open a **new terminal window** (keep the previous one running) and run:

```bash
ngrok http 8000
```

You will see output like this:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Copy the `https://` URL (yours will be different from the example above).

Now update `.env` — set `BASE_URL` to your ngrok URL:
```
BASE_URL=https://abc123.ngrok-free.app
```

Then restart the app in the first terminal:
```bash
docker compose up --build -d
```

---

### Step 6 — Connect Twilio to your app

1. Go to https://console.twilio.com
2. Click **Phone Numbers** → **Manage** → **Active Numbers**
3. Click your phone number
4. Under **Voice Configuration**, find **"A call comes in"**
5. Set it to **Webhook**, **HTTP POST**, and enter:
   ```
   https://abc123.ngrok-free.app/inbound
   ```
   (replace with your actual ngrok URL)
6. Click **Save**

---

### Step 7 — Call your number

Call your Twilio phone number from your mobile phone.

Alex will answer within 2-3 seconds and say:
> "Hi, this is Alex from Sears Home Services! How can I help you today?"

**Important:** On a Twilio trial account, you can only call from a verified phone number. To verify your number: Twilio Console → Phone Numbers → Verified Caller IDs → Add a new Caller ID.

---

## Testing Without a Phone Call

Use the included `chat.py` script to talk to the agent in your terminal — no phone needed, no per-minute cost:

```bash
docker compose exec app python chat.py
```

Type your messages and press Enter. The agent responds in text. This tests the full conversation logic including technician scheduling and photo upload links.

**Example session:**
```
You: my washing machine stopped draining
Alex: I'm sorry to hear that. Can you check if the drain hose at the back is kinked or blocked?
You: the hose looks fine
Alex: Let's try running a spin-only cycle — does the machine make any unusual sounds?
You: it hums but water doesn't drain
Alex: That sounds like the drain pump. Would you like me to schedule a technician?
You: yes, my zip is 60601
Alex: I found Marcus Rivera available Tuesday at 9 AM. Shall I book that?
```

---

## Running Tests

```bash
pytest tests/ -v
```

40 tests, all passing. No external services required — OpenAI, Deepgram, and Resend are mocked, SQLite is used instead of PostgreSQL.

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

**Tier 3 visual flow:**
```
Agent asks for email → Resend sends /upload/{token} link to caller's inbox
Caller opens link on phone → uploads photo
GPT-4o Vision analyzes photo → result fed back into the live conversation
```

See `docs/design.md` for full architectural details and technology decisions.

---

## Deploying to Railway (permanent URL, no ngrok needed)

1. Push to a GitHub repo
2. Go to https://railway.app → New Project → Deploy from GitHub repo
3. Select your repo
4. Add all environment variables from `.env` in the Railway dashboard
5. Railway gives you a permanent HTTPS URL — set that as `BASE_URL`
6. Update your Twilio webhook to the Railway URL

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
tests/            40 unit tests (SQLite, mocked external services)
chat.py           local chat test — talk to the agent without calling
docs/design.md    Technical design document
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key (GPT-4o + TTS) |
| `DATABASE_URL` | Yes | PostgreSQL connection string — use default value from `.env.example` |
| `TWILIO_ACCOUNT_SID` | For live calls | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | For live calls | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | For live calls | Your Twilio number in E.164 format (e.g. +16625919049) |
| `DEEPGRAM_API_KEY` | For live calls | Deepgram API key |
| `RESEND_API_KEY` | For Tier 3 | Resend API key — free plan sends only to your verified account email |
| `BASE_URL` | Yes | Your public URL from ngrok or Railway |

---

## Troubleshooting

**"An error has occurred — goodbye" when calling**
→ Your ngrok URL in the Twilio webhook is wrong or ngrok is not running. Repeat Steps 5 and 6.

**Agent doesn't answer (silence for 20+ seconds)**
→ Check `docker compose logs app` for errors. Make sure Docker Desktop is running.

**Email link shows "Link not found"**
→ Run chat.py as `docker compose exec app python chat.py` (not `python chat.py` directly). This ensures the token is saved to the correct database.

**Email not received**
→ Resend free plan only sends to your verified account email. Use the email address you signed up with at resend.com.
