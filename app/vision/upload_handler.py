import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.scheduling.models import ImageRequest
from app.vision.analyzer import analyze_image

router = APIRouter()

UPLOAD_DIR = "uploads"


async def analyze_and_store(req_id: int, image_path: str) -> None:
    """Background task: analyze uploaded image and store result.

    Opens its own DB session because the request session is closed by the
    time this coroutine runs.
    """
    from app.db import SessionLocal
    try:
        result = await analyze_image(image_path)
        db = SessionLocal()
        try:
            req = db.get(ImageRequest, req_id)
            if req:
                req.analysis_result = json.dumps(result)
                db.commit()
        finally:
            db.close()
    except Exception:
        pass


@router.get("/upload/{token}", response_class=HTMLResponse)
async def upload_form(token: str, db: Session = Depends(get_db)) -> str:
    req = db.query(ImageRequest).filter_by(token=token).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if req.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This upload link has expired")

    return f"""<!DOCTYPE html>
<html>
<head><title>Upload Appliance Photo — Sears Home Services</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{font-family:sans-serif;max-width:480px;margin:40px auto;padding:0 16px}}
button{{background:#003399;color:white;padding:12px 24px;border:none;border-radius:4px;cursor:pointer;font-size:16px}}</style>
</head>
<body>
<h2>Upload Your Appliance Photo</h2>
<p>Please upload a clear photo of the appliance. Our agent will use it to help diagnose the issue.</p>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="image" accept="image/*" capture="environment" required style="margin-bottom:16px;display:block">
  <button type="submit">Upload Photo</button>
</form>
</body>
</html>"""


@router.post("/upload/{token}", response_class=HTMLResponse)
async def upload_image(
    token: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> str:
    req = db.query(ImageRequest).filter_by(token=token).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if req.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This upload link has expired")

    upload_dir = Path(UPLOAD_DIR)
    upload_dir.mkdir(exist_ok=True)
    safe_name = f"{token}_{Path(image.filename).name if image.filename else 'photo.jpg'}"
    image_path = str(upload_dir / safe_name)
    contents = await image.read()
    with open(image_path, "wb") as f:
        f.write(contents)

    req.uploaded_at = datetime.now(timezone.utc)
    req.image_path = image_path
    db.commit()

    asyncio.create_task(analyze_and_store(req.id, image_path))

    return """<!DOCTYPE html>
<html>
<head><title>Photo Received — Sears Home Services</title>
<style>body{font-family:sans-serif;max-width:480px;margin:40px auto;padding:0 16px;text-align:center}</style>
</head>
<body>
<h2>Thank you!</h2>
<p>Your photo has been received. Our agent will use it to provide more specific guidance.</p>
<p>You can return to your phone call now.</p>
</body>
</html>"""
