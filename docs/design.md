# Technical Design Document
## Sears Home Services — Voice AI Agent

### Overview

This system accepts inbound phone calls and uses a voice AI agent to help homeowners diagnose appliance problems and schedule technician visits. When visual input would help diagnosis, the agent sends a unique email link, the caller uploads a photo, and GPT-4o Vision analyzes it and feeds the result back into the conversation.

---

### Architecture

The system is built around a real-time audio streaming pipeline with four layers:

**1. Telephony (Twilio)**
Twilio receives the inbound call and hits `POST /inbound` on the FastAPI server. The server returns TwiML instructing Twilio to open a bidirectional WebSocket (`/stream`). All audio — inbound from the caller and outbound from the agent — flows through this WebSocket for the duration of the call.

**2. Speech-to-Text (Deepgram Nova-2)**
The stream handler forwards incoming audio chunks (mulaw, 8kHz) to Deepgram over a second WebSocket. Deepgram returns finalized transcripts in near-real-time (~200ms). This streaming approach is fundamental to the UX — it allows the agent to begin processing as soon as the caller finishes speaking, rather than waiting for a full audio recording to be transcribed.

**3. LLM + Tools (GPT-4o)**
Each finalized transcript is appended to a per-call message history and sent to GPT-4o. The model decides whether to reply conversationally or invoke a tool. Tool calls are executed synchronously and their results fed back to the model before the final response is generated. Four tools are defined: `find_technicians`, `book_appointment`, `send_image_request`, and `get_image_analysis`.

**4. Text-to-Speech (OpenAI TTS)**
The agent's text response is synthesized to speech using OpenAI's `tts-1` model with the `shimmer` voice (PCM format, 24kHz). The audio is resampled to 8kHz and encoded as mulaw using Python's `audioop` module, then chunked and streamed back to Twilio.

**5. Barge-in (Interruption Handling)**
Audio is sent to Twilio in 100ms chunks. When Deepgram detects the caller speaking mid-response, the stream handler sets an `agent_speaking = False` flag, which stops chunk delivery, sends a Twilio `clear` event to flush the playback buffer, and discards any queued responses. This gives the caller natural control over the conversation pace.

**6. Visual Diagnosis (Tier 3)**
When the agent determines a photo would help, it calls `send_image_request` — this generates a UUID token, stores it in the database, and sends an email via Resend with a link to `GET /upload/{token}`. The caller opens the link on their phone and submits a photo. The upload endpoint saves the image and triggers an async GPT-4o Vision call in a fresh database session (independent of the closed request session). The agent can retrieve the result mid-call via `get_image_analysis`.

---

### Technology Decisions

**Python + FastAPI** was chosen for its first-class async WebSocket support and the richness of the Python AI/voice ecosystem. FastAPI's dependency injection made it straightforward to pass a database session into route handlers and the tool dispatch layer without global state.

**Deepgram over OpenAI Whisper** — Deepgram streams partial and finalized transcripts over WebSocket in near-real-time. Whisper requires a complete audio clip before returning any result, which adds 1–3 seconds of dead air per conversational turn. For a phone call, that latency is unacceptable; callers would hang up.

**GPT-4o over OpenAI Realtime API** — The Realtime API offers lower raw latency but has limited structured tool call support, which is central to the scheduling and vision workflows. The modular pipeline (separate STT → LLM → TTS stages) adds roughly 300–500ms compared to a fully integrated solution, but provides full control over each layer, is much easier to debug, and keeps the Tier 3 visual workflow cleanly decoupled.

**Implicit conversation state** — Rather than maintaining a separate finite state machine, conversation state is carried entirely in the GPT-4o message history. This keeps the codebase simple and leverages the model's strong contextual understanding. The system prompt defines the expected conversation stages (GREET → IDENTIFY_APPLIANCE → COLLECT_SYMPTOMS → DIAGNOSE → SCHEDULE → CLOSE) and instructs the model to progress through them naturally without requiring explicit state transitions in code.

**Railway over AWS/GCP** — This is a demo with a known testing window. Railway deploys a Docker Compose file directly from a GitHub repository in under two minutes with no infrastructure configuration. Production would use ECS or Cloud Run with proper secrets management, horizontal scaling, and Redis for session storage.

---

### Trade-offs and Limitations

**Latency** — End-to-end response latency is approximately 1.0–1.5 seconds per turn (Deepgram ~200ms + GPT-4o ~600ms + TTS ~300ms + network). This is appropriate for an appliance troubleshooting call. Further reduction would require the OpenAI Realtime API or LLM response streaming with incremental TTS synthesis.

**In-memory session store** — Conversation history is stored in a Python dictionary keyed by Twilio `CallSid`. A server restart clears all active sessions mid-call. Production would replace this with a Redis store with per-call TTL.

**Single-server WebSocket** — The WebSocket connection is pinned to one server process. Horizontal scaling requires sticky sessions or moving the audio relay to a message broker (e.g., Redis Pub/Sub).

**No Twilio signature validation** — The `/inbound` webhook does not verify the `X-Twilio-Signature` header. Any HTTP client that knows the URL can trigger call sessions. This must be added before production deployment.

**`audioop` deprecation** — The `audioop` module (used for PCM→mulaw conversion) is deprecated in Python 3.12 and removed in 3.13. The Dockerfile pins `python:3.12-slim`. A replacement using `numpy` + `scipy` or the `soundfile` library should be implemented before upgrading the runtime.

**Unbounded conversation history** — Message history grows for the duration of the call with no trimming. Very long calls (30+ turns) could exceed GPT-4o's context window. Production would cap history at a fixed token budget, summarizing older turns.
