from openai import AsyncOpenAI
from app.config import settings
from app.agent.audio import pcm24k_to_mulaw8k

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def synthesize_to_mulaw(text: str) -> bytes:
    """Synthesize text to speech and return mulaw 8kHz bytes for Twilio."""
    response = await openai_client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
        response_format="pcm",  # 24kHz, 16-bit mono, little-endian
    )
    return pcm24k_to_mulaw8k(response.content)
