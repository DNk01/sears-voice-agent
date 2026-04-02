from app.scheduling.models import Technician, ServiceArea, Specialty, AvailabilitySlot, Appointment, ImageRequest


def test_technician_model_has_required_columns():
    cols = {c.key for c in Technician.__table__.columns}
    assert {"id", "name", "email", "phone"} <= cols


def test_availability_slot_model_has_is_booked():
    cols = {c.key for c in AvailabilitySlot.__table__.columns}
    assert "is_booked" in cols


def test_image_request_model_has_token_and_session():
    cols = {c.key for c in ImageRequest.__table__.columns}
    assert {"token", "session_id", "analysis_result", "expires_at"} <= cols
