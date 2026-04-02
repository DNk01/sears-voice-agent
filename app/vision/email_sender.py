import resend
from app.config import settings

resend.api_key = settings.resend_api_key


async def send_upload_link(email: str, token: str, base_url: str) -> None:
    """Send an email with a unique appliance photo upload link."""
    upload_url = f"{base_url}/upload/{token}"
    resend.Emails.send({
        "from": "Sears Home Services <noreply@resend.dev>",
        "to": [email],
        "subject": "Upload your appliance photo — Sears Home Services",
        "html": f"""
        <p>Hi,</p>
        <p>Our service agent has requested a photo of your appliance to help diagnose the issue.</p>
        <p><a href="{upload_url}" style="background:#003399;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;display:inline-block;">
          Upload Photo
        </a></p>
        <p>Or copy this link into your browser:<br><code>{upload_url}</code></p>
        <p>This link expires in 24 hours.</p>
        <p>— Sears Home Services</p>
        """,
    })
