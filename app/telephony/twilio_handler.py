from fastapi import APIRouter, Request, Response
from app.config import settings

router = APIRouter()


@router.post("/inbound")
async def inbound(request: Request) -> Response:
    """Handle incoming Twilio call. Returns TwiML to open a Media Stream."""
    ws_url = settings.base_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{ws_url}/stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}" />
  </Connect>
</Response>"""

    return Response(content=twiml, media_type="text/xml")
