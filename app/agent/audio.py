import audioop


def pcm24k_to_mulaw8k(pcm_data: bytes) -> bytes:
    """Convert 24kHz 16-bit PCM (from OpenAI TTS) to 8kHz mulaw (for Twilio)."""
    resampled, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
    return audioop.lin2ulaw(resampled, 2)


def chunk_audio(audio: bytes, chunk_size: int = 8000) -> list[bytes]:
    """Split audio into fixed-size chunks."""
    if not audio:
        return []
    return [audio[i: i + chunk_size] for i in range(0, len(audio), chunk_size)]
