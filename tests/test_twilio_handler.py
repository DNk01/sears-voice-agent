def test_inbound_returns_twiml_with_stream(client):
    response = client.post("/inbound", data={"CallSid": "CA123", "From": "+13125550000"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/xml")
    body = response.text
    assert "<Connect>" in body
    assert "<Stream" in body
    assert "/stream" in body


def test_inbound_twiml_has_ws_url(client):
    response = client.post("/inbound", data={"CallSid": "CA123"})
    assert "wss://" in response.text or "ws://" in response.text


def test_stream_route_is_registered(client):
    from app.main import app
    routes = {r.path for r in app.routes}
    assert "/stream" in routes


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
