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


# --- Scheduling query tests ---

from app.scheduling.queries import find_technicians, book_appointment, create_image_request, get_image_analysis
import pytest


def test_find_technicians_returns_matching_results(db):
    seed_database(db)
    results = find_technicians("60601", "washer", db)
    assert len(results) > 0
    assert len(results) <= 3
    first = results[0]
    assert {"technician_id", "technician_name", "slot_id", "start_time", "end_time"} <= first.keys()


def test_find_technicians_returns_empty_for_no_match(db):
    seed_database(db)
    results = find_technicians("99999", "washer", db)
    assert results == []


def test_book_appointment_creates_record_and_marks_slot(db):
    seed_database(db)
    options = find_technicians("60601", "washer", db)
    assert len(options) > 0
    opt = options[0]
    result = book_appointment(
        tech_id=opt["technician_id"],
        slot_id=opt["slot_id"],
        customer_name="Jane Smith",
        customer_phone="312-555-9999",
        customer_email="jane@example.com",
        appliance_type="washer",
        zip_code="60601",
        db=db,
    )
    assert result["appointment_id"] is not None
    assert result["technician_name"] == opt["technician_name"]
    slot = db.get(AvailabilitySlot, opt["slot_id"])
    assert slot.is_booked is True


def test_book_appointment_raises_if_slot_already_booked(db):
    seed_database(db)
    options = find_technicians("60601", "washer", db)
    opt = options[0]
    book_appointment(opt["technician_id"], opt["slot_id"], "A", "111", None, "washer", "60601", db)
    with pytest.raises(ValueError, match="already booked"):
        book_appointment(opt["technician_id"], opt["slot_id"], "B", "222", None, "washer", "60601", db)


def test_create_and_get_image_request(db):
    token = create_image_request("CA1234567890", "user@example.com", db)
    assert len(token) == 36
    result = get_image_analysis("CA1234567890", db)
    assert result is None


def test_get_image_analysis_returns_result_after_upload(db):
    import json
    token = create_image_request("CA_TEST_SESSION", "test@example.com", db)
    req = db.query(ImageRequest).filter_by(token=token).first()
    req.analysis_result = json.dumps({"appliance_type": "washer", "issues": ["rust on drum"]})
    req.uploaded_at = datetime.now(timezone.utc)
    db.commit()
    result = get_image_analysis("CA_TEST_SESSION", db)
    assert result is not None
    assert result["appliance_type"] == "washer"
