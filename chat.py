"""
Local chat test — simulates a call without Twilio/Deepgram/TTS.
Talks directly to the agent's conversation logic (GPT-4o + tools).

Usage:
    python chat.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent))

# Use the same PostgreSQL as the running Docker app so tokens are shared
os.environ["DATABASE_URL"] = "postgresql://sears:sears@localhost:5433/sears"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.scheduling.models  # noqa — registers models
from app.db import Base
from app.agent.conversation import process_transcript, clear_session
from app.scheduling.seed import seed_database

SESSION_ID = "local-test-call-001"

def setup_db():
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_database(db)
    return db

async def main():
    print("=" * 55)
    print("  Sears Voice Agent — local chat test")
    print("  Type your message, Enter to send. Ctrl+C to quit.")
    print("=" * 55)
    print()

    db = setup_db()

    # Kick off the conversation — agent greets first
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
