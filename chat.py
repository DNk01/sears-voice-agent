"""
Local chat test — simulates a call without Twilio/Deepgram/TTS.
Talks directly to the agent's conversation logic (GPT-4o + tools).

Run inside Docker (recommended — shares PostgreSQL with the running app):
    docker compose exec app python chat.py

Run from host (requires Docker port 5433 exposed):
    python chat.py
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Must be set before any app imports so pydantic-settings picks it up
os.environ["DATABASE_URL"] = "postgresql://sears:sears@db:5432/sears"

import app.scheduling.models  # noqa — registers models with Base
from app.db import SessionLocal
from app.agent.conversation import process_transcript, clear_session
from app.scheduling.seed import seed_database

SESSION_ID = "local-test-call-001"


async def main():
    print("=" * 55)
    print("  Sears Voice Agent — local chat test")
    print("  Type your message, Enter to send. Ctrl+C to quit.")
    print("=" * 55)
    print()

    db = SessionLocal()
    seed_database(db)

    print("Alex: ", end="", flush=True)
    greeting = await process_transcript(SESSION_ID, "[call connected]", db)
    print(greeting)
    print()

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not user_input:
                continue

            print("Alex: ", end="", flush=True)
            reply = await process_transcript(SESSION_ID, user_input, db)
            print(reply)
            print()
    except KeyboardInterrupt:
        pass
    finally:
        clear_session(SESSION_ID)
        db.close()
        print("\n[call ended]")


if __name__ == "__main__":
    asyncio.run(main())
