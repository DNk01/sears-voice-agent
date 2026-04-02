import io
import json
import pytest
from datetime import datetime, timedelta, timezone
from app.scheduling.models import ImageRequest


def _insert_token(db, token: str, session_id: str = "CA_UPLOAD_TEST", expired: bool = False):
    expires = datetime.now(timezone.utc) + (timedelta(hours=-1) if expired else timedelta(hours=24))
    req = ImageRequest(
        session_id=session_id,
        token=token,
        email="test@example.com",
        expires_at=expires,
    )
    db.add(req)
    db.commit()
    return req


def test_upload_get_returns_html_form(client, db):
    _insert_token(db, "valid-token-001")
    response = client.get("/upload/valid-token-001")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<form" in response.text


def test_upload_get_expired_token_returns_410(client, db):
    _insert_token(db, "expired-token", expired=True)
    response = client.get("/upload/expired-token")
    assert response.status_code == 410


def test_upload_get_missing_token_returns_404(client, db):
    response = client.get("/upload/nonexistent-token-xyz")
    assert response.status_code == 404


def test_upload_post_saves_image(client, db, mocker, tmp_path):
    mocker.patch("app.vision.upload_handler.UPLOAD_DIR", str(tmp_path))
    mocker.patch("app.vision.upload_handler.analyze_and_store", return_value=None)
    _insert_token(db, "post-token-001")
    file_content = b"fake image bytes"
    response = client.post(
        "/upload/post-token-001",
        files={"image": ("test.jpg", io.BytesIO(file_content), "image/jpeg")},
    )
    assert response.status_code == 200
    assert "thank" in response.text.lower() or "received" in response.text.lower()


@pytest.mark.asyncio
async def test_send_upload_link_calls_resend(mocker):
    mock_send = mocker.patch("resend.Emails.send", return_value={"id": "abc123"})
    from app.vision.email_sender import send_upload_link
    await send_upload_link("customer@example.com", "test-token-uuid", "https://example.com")
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args[0][0]
    assert call_kwargs["to"] == ["customer@example.com"]
    assert "test-token-uuid" in call_kwargs["html"]


@pytest.mark.asyncio
async def test_send_upload_link_includes_correct_url(mocker):
    mocker.patch("resend.Emails.send", return_value={"id": "abc123"})
    from app.vision.email_sender import send_upload_link
    await send_upload_link("user@example.com", "my-token", "https://myapp.railway.app")
    import resend
    call_kwargs = resend.Emails.send.call_args[0][0]
    assert "https://myapp.railway.app/upload/my-token" in call_kwargs["html"]


@pytest.mark.asyncio
async def test_analyze_image_returns_structured_result(mocker, tmp_path):
    fake_image = tmp_path / "appliance.jpg"
    fake_image.write_bytes(b"fake image data")

    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "appliance_type": "washer",
        "visible_issues": ["rust around door seal"],
        "error_codes": [],
        "recommendations": ["Replace door seal gasket"],
    })
    mocker.patch(
        "app.vision.analyzer.openai_client.chat.completions.create",
        new=mocker.AsyncMock(return_value=mock_response),
    )

    from app.vision.analyzer import analyze_image
    result = await analyze_image(str(fake_image))
    assert result["appliance_type"] == "washer"
    assert "recommendations" in result


@pytest.mark.asyncio
async def test_analyze_image_handles_non_json_response(mocker, tmp_path):
    fake_image = tmp_path / "appliance.jpg"
    fake_image.write_bytes(b"fake image data")

    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "I can see a washing machine with some rust."
    mocker.patch(
        "app.vision.analyzer.openai_client.chat.completions.create",
        new=mocker.AsyncMock(return_value=mock_response),
    )

    from app.vision.analyzer import analyze_image
    result = await analyze_image(str(fake_image))
    assert "raw_description" in result
