from datetime import datetime, timezone
from app.scheduling.models import Technician, ServiceArea, Specialty, AvailabilitySlot, Appointment, ImageRequest
from app.scheduling.seed import seed_database


def test_technician_model_has_required_columns():
    cols = {c.key for c in Technician.__table__.columns}
    assert {"id", "name", "email", "phone"} <= cols


def test_availability_slot_model_has_is_booked():
    cols = {c.key for c in AvailabilitySlot.__table__.columns}
    assert "is_booked" in cols


def test_image_request_model_has_token_and_session():
    cols = {c.key for c in ImageRequest.__table__.columns}
    assert {"token", "session_id", "analysis_result", "expires_at"} <= cols


def test_seed_creates_10_technicians(db):
    seed_database(db)
    count = db.query(Technician).count()
    assert count == 10


def test_seed_technicians_have_service_areas(db):
    seed_database(db)
    count = db.query(ServiceArea).count()
    assert count >= 10


def test_seed_slots_are_in_the_future(db):
    seed_database(db)
    future_slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.start_time > datetime.now(timezone.utc)
    ).count()
    assert future_slots >= 50
