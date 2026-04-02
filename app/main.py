from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.db import engine, SessionLocal, Base
from app.telephony.twilio_handler import router as twilio_router
from app.telephony.stream_handler import router as stream_router
from app.vision.upload_handler import router as upload_router
import app.scheduling.models  # noqa: F401 — registers models with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.scheduling.seed import seed_database
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Sears Home Services Voice Agent", lifespan=lifespan)
app.include_router(twilio_router)
app.include_router(stream_router)
app.include_router(upload_router)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
