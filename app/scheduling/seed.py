from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.scheduling.models import Technician, ServiceArea, Specialty, AvailabilitySlot

TECHNICIANS = [
    {"name": "Marcus Rivera",   "email": "m.rivera@sears.com",   "phone": "312-555-0101",
     "zips": ["60601", "60611"], "specialties": ["washer", "dryer"]},
    {"name": "Diana Chen",      "email": "d.chen@sears.com",     "phone": "312-555-0102",
     "zips": ["60614", "60657"], "specialties": ["refrigerator", "dishwasher"]},
    {"name": "James Okafor",    "email": "j.okafor@sears.com",   "phone": "312-555-0103",
     "zips": ["60640", "60657"], "specialties": ["oven", "hvac"]},
    {"name": "Sofia Petrov",    "email": "s.petrov@sears.com",   "phone": "312-555-0104",
     "zips": ["60601", "60614"], "specialties": ["washer", "refrigerator", "dishwasher"]},
    {"name": "Tyrone Williams", "email": "t.williams@sears.com", "phone": "312-555-0105",
     "zips": ["60611", "60640"], "specialties": ["hvac", "dryer"]},
    {"name": "Priya Patel",     "email": "p.patel@sears.com",    "phone": "312-555-0106",
     "zips": ["60657", "60611"], "specialties": ["oven", "refrigerator"]},
    {"name": "Carlos Mendez",   "email": "c.mendez@sears.com",   "phone": "312-555-0107",
     "zips": ["60601", "60640"], "specialties": ["washer", "dryer", "dishwasher"]},
    {"name": "Amara Nwosu",     "email": "a.nwosu@sears.com",    "phone": "312-555-0108",
     "zips": ["60614", "60611"], "specialties": ["refrigerator", "hvac"]},
    {"name": "Kevin Zhang",     "email": "k.zhang@sears.com",    "phone": "312-555-0109",
     "zips": ["60640", "60601"], "specialties": ["oven", "washer"]},
    {"name": "Rachel Torres",   "email": "r.torres@sears.com",   "phone": "312-555-0110",
     "zips": ["60657", "60614"], "specialties": ["dryer", "dishwasher", "oven"]},
]


def seed_database(db: Session) -> None:
    """Idempotent: skips if technicians already exist."""
    if db.query(Technician).count() > 0:
        return

    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    slot_hours = [9, 11, 13, 15, 17]

    for i, data in enumerate(TECHNICIANS):
        tech = Technician(name=data["name"], email=data["email"], phone=data["phone"])
        db.add(tech)
        db.flush()

        for z in data["zips"]:
            db.add(ServiceArea(technician_id=tech.id, zip_code=z))

        for s in data["specialties"]:
            db.add(Specialty(technician_id=tech.id, appliance_type=s))

        day_start = base.replace(hour=0, minute=0)
        for day in range(1, 8):
            hour = slot_hours[(i + day) % len(slot_hours)]
            start = day_start + timedelta(days=day, hours=hour)
            db.add(AvailabilitySlot(
                technician_id=tech.id,
                start_time=start,
                end_time=start + timedelta(hours=2),
                is_booked=False,
            ))

    db.commit()
