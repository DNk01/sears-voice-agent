import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_process_transcript_returns_string(db, mocker):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hi, this is Alex from Sears Home Services!"
    mock_response.choices[0].message.tool_calls = None

    mocker.patch("app.agent.conversation.openai_client.chat.completions.create",
                 new=AsyncMock(return_value=mock_response))

    from app.agent.conversation import process_transcript, _sessions
    _sessions.clear()

    result = await process_transcript("CA_SESSION_001", "Hello", db)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_process_transcript_maintains_history(db, mocker):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Got it — a washer."
    mock_response.choices[0].message.tool_calls = None

    create_mock = AsyncMock(return_value=mock_response)
    mocker.patch("app.agent.conversation.openai_client.chat.completions.create", new=create_mock)

    from app.agent.conversation import process_transcript, _sessions
    _sessions.clear()

    await process_transcript("CA_SESSION_002", "My washer is broken", db)
    await process_transcript("CA_SESSION_002", "It stopped mid-cycle", db)

    call_args_list = create_mock.call_args_list
    first_count = len(call_args_list[0].kwargs["messages"])
    second_count = len(call_args_list[1].kwargs["messages"])
    assert second_count > first_count


@pytest.mark.asyncio
async def test_process_transcript_executes_tool_call(db, mocker):
    import json

    tool_call = MagicMock()
    tool_call.id = "call_abc123"
    tool_call.function.name = "find_technicians"
    tool_call.function.arguments = json.dumps({"zip_code": "60601", "appliance_type": "washer"})

    first_response = MagicMock()
    first_response.choices = [MagicMock()]
    first_response.choices[0].message.content = None
    first_response.choices[0].message.tool_calls = [tool_call]

    second_response = MagicMock()
    second_response.choices = [MagicMock()]
    second_response.choices[0].message.content = "I found a few technicians for you."
    second_response.choices[0].message.tool_calls = None

    create_mock = AsyncMock(side_effect=[first_response, second_response])
    mocker.patch("app.agent.conversation.openai_client.chat.completions.create", new=create_mock)
    mocker.patch("app.agent.conversation.dispatch_tool", new=AsyncMock(return_value="[]"))

    from app.agent.conversation import process_transcript, _sessions
    _sessions.clear()

    result = await process_transcript("CA_SESSION_003", "I need a technician", db)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_clear_session_removes_history(db, mocker):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello!"
    mock_response.choices[0].message.tool_calls = None
    mocker.patch("app.agent.conversation.openai_client.chat.completions.create",
                 new=AsyncMock(return_value=mock_response))

    from app.agent.conversation import process_transcript, clear_session, _sessions
    _sessions.clear()

    await process_transcript("CA_CLEAR_TEST", "hi", db)
    assert "CA_CLEAR_TEST" in _sessions

    clear_session("CA_CLEAR_TEST")
    assert "CA_CLEAR_TEST" not in _sessions
