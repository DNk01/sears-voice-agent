import json
import pytest
from app.agent.tools import TOOL_SCHEMAS, dispatch_tool


def test_tool_schemas_has_four_tools():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert names == {"find_technicians", "book_appointment", "send_image_request", "get_image_analysis"}


def test_tool_schemas_are_valid_openai_format():
    for schema in TOOL_SCHEMAS:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert "name" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"


@pytest.mark.asyncio
async def test_dispatch_find_technicians(db):
    from app.scheduling.seed import seed_database
    seed_database(db)
    result = await dispatch_tool("find_technicians", {"zip_code": "60601", "appliance_type": "washer"}, db)
    data = json.loads(result)
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error(db):
    result = await dispatch_tool("nonexistent_tool", {}, db)
    assert "unknown tool" in result.lower()


@pytest.mark.asyncio
async def test_dispatch_send_image_request(db, mocker):
    mocker.patch("app.agent.tools.send_upload_link", return_value=None)
    result = await dispatch_tool(
        "send_image_request",
        {"email": "test@example.com", "session_id": "CA_TEST"},
        db,
    )
    assert "link" in result.lower() or "sent" in result.lower()
