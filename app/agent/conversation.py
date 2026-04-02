import json
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_SCHEMAS, dispatch_tool

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

# In-memory session store keyed by Twilio CallSid
_sessions: dict[str, list[dict]] = {}


def _get_history(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return _sessions[session_id]


async def process_transcript(session_id: str, text: str, db: Session) -> str:
    """Process a caller utterance and return the agent's text response."""
    history = _get_history(session_id)
    history.append({"role": "user", "content": text})

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=list(history),  # pass a snapshot so call_args reflects state at call time
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
    )

    message = response.choices[0].message

    # Handle tool calls (may chain multiple rounds)
    while message.tool_calls:
        history.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            result = await dispatch_tool(tc.function.name, args, db)
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        message = response.choices[0].message

    reply = message.content or ""
    history.append({"role": "assistant", "content": reply})
    return reply


def clear_session(session_id: str) -> None:
    """Remove session from memory when the call ends."""
    _sessions.pop(session_id, None)
