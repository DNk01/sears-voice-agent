import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from sqlalchemy.orm import Session

from app.config import settings
from app.agent.conversation import process_transcript, clear_session
from app.agent.tts import synthesize_to_mulaw
from app.agent.audio import chunk_audio
from app.db import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter()

deepgram_client = DeepgramClient(api_key=settings.deepgram_api_key)


@dataclass
class CallSession:
    session_id: str = ""
    stream_sid: str = ""
    transcript_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    active: bool = True
    agent_speaking: bool = False


async def _send_audio_to_twilio(websocket: WebSocket, session: "CallSession", mulaw_audio: bytes) -> None:
    """Send mulaw audio chunks to Twilio. Stops immediately on barge-in."""
    session.agent_speaking = True
    try:
        for chunk in chunk_audio(mulaw_audio, chunk_size=800):  # 100ms chunks for responsive barge-in
            if not session.agent_speaking:
                # Caller started speaking — clear Twilio's audio buffer and stop
                await websocket.send_text(json.dumps({
                    "event": "clear",
                    "streamSid": session.stream_sid,
                }))
                return
            payload = base64.b64encode(chunk).decode("utf-8")
            await websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": session.stream_sid,
                "media": {"payload": payload},
            }))
    finally:
        session.agent_speaking = False


@router.websocket("/stream")
async def stream_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    session = CallSession()
    db: Session = SessionLocal()

    dg_connection = deepgram_client.listen.asyncwebsocket.v("1")

    async def on_transcript(self, result, **kwargs):  # noqa: N805
        try:
            alt = result.channel.alternatives[0]
            if result.is_final and alt.transcript.strip():
                # Barge-in: stop agent and discard queued responses
                if session.agent_speaking:
                    session.agent_speaking = False
                    while not session.transcript_queue.empty():
                        session.transcript_queue.get_nowait()
                await session.transcript_queue.put(alt.transcript.strip())
        except Exception as e:
            logger.warning("Transcript parsing error: %s", e)

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)

    await dg_connection.start(LiveOptions(
        encoding="mulaw",
        sample_rate=8000,
        channels=1,
        model="nova-2",
        language="en-US",
        smart_format=True,
        endpointing=500,
    ))

    async def receive_from_twilio():
        try:
            async for raw in websocket.iter_text():
                data = json.loads(raw)
                event = data.get("event")
                if event == "start":
                    session.session_id = data["start"]["callSid"]
                    session.stream_sid = data["streamSid"]
                    logger.info("Call started: %s", session.session_id)
                elif event == "media" and session.stream_sid:
                    audio = base64.b64decode(data["media"]["payload"])
                    await dg_connection.send(audio)
                elif event == "stop":
                    session.active = False
                    await dg_connection.finish()
        except WebSocketDisconnect:
            session.active = False
            await dg_connection.finish()

    async def process_transcripts():
        while not session.session_id and session.active:
            await asyncio.sleep(0.05)

        # Send greeting immediately when call connects — no need to wait for caller to speak
        try:
            greeting = await process_transcript(session.session_id, "[call connected]", db)
            if greeting and session.stream_sid:
                audio = await synthesize_to_mulaw(greeting)
                await _send_audio_to_twilio(websocket, session, audio)
        except Exception as e:
            logger.error("Error sending greeting: %s", e)

        while session.active or not session.transcript_queue.empty():
            try:
                transcript = await asyncio.wait_for(session.transcript_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            try:
                reply = await process_transcript(session.session_id, transcript, db)
                if reply and session.stream_sid:
                    audio = await synthesize_to_mulaw(reply)
                    await _send_audio_to_twilio(websocket, session, audio)
            except Exception as e:
                logger.error("Error processing transcript: %s", e)

    try:
        await asyncio.gather(receive_from_twilio(), process_transcripts())
    finally:
        clear_session(session.session_id)
        db.close()
