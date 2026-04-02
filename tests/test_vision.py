import io
import json
import pytest
from datetime import datetime, timedelta, timezone
from app.scheduling.models import ImageRequest
from app.scheduling.queries import create_image_request, get_image_analysis


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


@pytest.mark.asyncio
async def test_analyze_and_store_persists_result_to_db(db, mocker, tmp_path):
    """analyze_and_store must write analysis_result using its own session.

    This guards against the bug where the background task received a closed
    request-scoped session and silently failed to save the result.
    """
    # Arrange: create token in DB and write a fake image
    token = create_image_request("CA_BG_TEST", "test@example.com", db)
    fake_image = tmp_path / "appliance.jpg"
    fake_image.write_bytes(b"fake image data")

    # Patch SessionLocal so the background task uses the same test DB session
    mocker.patch("app.db.SessionLocal", return_value=db)

    analysis = {"appliance_type": "washer", "visible_issues": ["rust"]}
    mocker.patch(
        "app.vision.upload_handler.analyze_image",
        new=mocker.AsyncMock(return_value=analysis),
    )

    # Act: run the background task directly
    from app.vision.upload_handler import analyze_and_store
    req = db.query(ImageRequest).filter_by(token=token).first()
    await analyze_and_store(req.id, str(fake_image))

    # Assert: result is saved in DB and readable via get_image_analysis
    db.expire_all()  # force re-read from DB
    result = get_image_analysis("CA_BG_TEST", db)
    assert result is not None
    assert result["appliance_type"] == "washer"
    assert "rust" in result["visible_issues"]


@pytest.mark.asyncio
async def test_full_tier3_flow(client, db, mocker, tmp_path):
    """End-to-end Tier 3: upload image → analysis stored → agent can retrieve it."""
    # Create token
    token = create_image_request("CA_E2E_TEST", "test@example.com", db)

    # Mock the background analysis
    analysis = {"appliance_type": "oven", "visible_issues": ["burnt element"], "recommendations": ["replace element"]}
    mock_store = mocker.patch(
        "app.vision.upload_handler.analyze_and_store",
        new=mocker.AsyncMock(return_value=None),
    )
    mocker.patch("app.vision.upload_handler.UPLOAD_DIR", str(tmp_path))

    # Upload image via HTTP
    response = client.post(
        f"/upload/{token}",
        files={"image": ("oven.jpg", io.BytesIO(b"fake oven image"), "image/jpeg")},
    )
    assert response.status_code == 200
    assert "thank" in response.text.lower()

    # Verify background task was triggered with correct args
    mock_store.assert_called_once()
    call_args = mock_store.call_args[0]
    req = db.query(ImageRequest).filter_by(token=token).first()
    assert call_args[0] == req.id  # correct req_id

    # Simulate analysis completing (write result directly)
    req.analysis_result = json.dumps(analysis)
    db.commit()

    # Agent tool should now return the result
    result = get_image_analysis("CA_E2E_TEST", db)
    assert result is not None
    assert result["appliance_type"] == "oven"
