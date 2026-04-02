import json
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.scheduling.models import (
    Technician, ServiceArea, Specialty, AvailabilitySlot, Appointment, ImageRequest
)


def find_technicians(zip_code: str, appliance_type: str, db: Session) -> list[dict]:
    """Return up to 3 available technicians matching zip and appliance type."""
    rows = (
        db.query(Technician, AvailabilitySlot)
        .join(ServiceArea, ServiceArea.technician_id == Technician.id)
        .join(Specialty, Specialty.technician_id == Technician.id)
        .join(AvailabilitySlot, AvailabilitySlot.technician_id == Technician.id)
        .filter(
            ServiceArea.zip_code == zip_code,
            Specialty.appliance_type == appliance_type,
            AvailabilitySlot.is_booked == False,  # noqa: E712
            AvailabilitySlot.start_time > datetime.now(timezone.utc),
        )
        .order_by(AvailabilitySlot.start_time.asc())
        .limit(3)
        .all()
    )
    return [
        {
            "technician_id": tech.id,
            "technician_name": tech.name,
            "slot_id": slot.id,
            "start_time": slot.start_time.strftime("%A, %B %d at %I:%M %p").replace(" 0", " "),
            "end_time": slot.end_time.strftime("%I:%M %p").lstrip("0"),
        }
        for tech, slot in rows
    ]


def book_appointment(
    tech_id: int,
    slot_id: int,
    customer_name: str,
    customer_phone: str,
    customer_email: str | None,
    appliance_type: str,
    zip_code: str,
    db: Session,
) -> dict:
    """Book an appointment. Raises ValueError if slot is already booked."""
    slot = db.get(AvailabilitySlot, slot_id)
    if slot is None or slot.is_booked:
        raise ValueError(f"Slot {slot_id} is already booked or does not exist")

    slot.is_booked = True
    appt = Appointment(
        technician_id=tech_id,
        slot_id=slot_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        appliance_type=appliance_type,
        zip_code=zip_code,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    tech = db.get(Technician, tech_id)
    return {
        "appointment_id": appt.id,
        "technician_name": tech.name,
        "start_time": slot.start_time.strftime("%A, %B %d at %I:%M %p").replace(" 0", " "),
        "end_time": slot.end_time.strftime("%I:%M %p").lstrip("0"),
    }


def create_image_request(session_id: str, email: str, db: Session) -> str:
    """Create a new image upload request. Returns the upload token (UUID)."""
    token = str(uuid.uuid4())
    req = ImageRequest(
        session_id=session_id,
        token=token,
        email=email,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(req)
    db.commit()
    return token


def get_image_analysis(session_id: str, db: Session) -> dict | None:
    """Return parsed analysis result for the session, or None if not yet uploaded."""
    req = (
        db.query(ImageRequest)
        .filter_by(session_id=session_id)
        .order_by(ImageRequest.created_at.desc())
        .first()
    )
    if req is None or req.analysis_result is None:
        return None
    return json.loads(req.analysis_result)
