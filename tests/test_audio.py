import pytest
from app.agent.audio import pcm24k_to_mulaw8k, chunk_audio


def test_pcm24k_to_mulaw8k_returns_bytes():
    silence_pcm = b"\x00\x00" * 2400
    result = pcm24k_to_mulaw8k(silence_pcm)
    assert isinstance(result, bytes)


def test_pcm24k_to_mulaw8k_reduces_sample_rate():
    pcm_24k = b"\x00\x00" * 2400  # 2400 samples at 24kHz = 0.1s
    result = pcm24k_to_mulaw8k(pcm_24k)
    # At 8kHz, 0.1s = ~800 samples, 1 byte each (mulaw)
    assert 700 <= len(result) <= 900


def test_chunk_audio_splits_correctly():
    audio = bytes(range(256)) * 40  # 10240 bytes
    chunks = chunk_audio(audio, chunk_size=4000)
    assert len(chunks) == 3
    assert len(chunks[0]) == 4000
    assert len(chunks[1]) == 4000
    assert len(chunks[2]) == 2240


def test_chunk_audio_empty_returns_empty():
    assert chunk_audio(b"") == []


@pytest.mark.asyncio
async def test_synthesize_to_mulaw_calls_openai(mocker):
    from app.agent.tts import synthesize_to_mulaw
    fake_pcm = b"\x00\x00" * 2400
    mock_response = mocker.MagicMock()
    mock_response.content = fake_pcm
    mocker.patch(
        "app.agent.tts.openai_client.audio.speech.create",
        new=mocker.AsyncMock(return_value=mock_response),
    )
    result = await synthesize_to_mulaw("Hello, how can I help?")
    assert isinstance(result, bytes)
    assert len(result) > 0
