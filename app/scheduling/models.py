import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base


class ApplianceType(str, enum.Enum):
    WASHER = "washer"
    DRYER = "dryer"
    REFRIGERATOR = "refrigerator"
    DISHWASHER = "dishwasher"
    OVEN = "oven"
    HVAC = "hvac"
    OTHER = "other"


class Technician(Base):
    __tablename__ = "technicians"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    service_areas = relationship("ServiceArea", back_populates="technician", cascade="all, delete-orphan")
    specialties = relationship("Specialty", back_populates="technician", cascade="all, delete-orphan")
    availability_slots = relationship("AvailabilitySlot", back_populates="technician", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="technician")


class ServiceArea(Base):
    __tablename__ = "service_areas"
    id = Column(Integer, primary_key=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    zip_code = Column(String(10), nullable=False)
    technician = relationship("Technician", back_populates="service_areas")


class Specialty(Base):
    __tablename__ = "specialties"
    id = Column(Integer, primary_key=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    appliance_type = Column(String(50), nullable=False)
    technician = relationship("Technician", back_populates="specialties")


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"
    id = Column(Integer, primary_key=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False, nullable=False)
    technician = relationship("Technician", back_populates="availability_slots")
    appointment = relationship("Appointment", back_populates="slot", uselist=False)


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("availability_slots.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    customer_email = Column(String)
    appliance_type = Column(String(50), nullable=False)
    zip_code = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    technician = relationship("Technician", back_populates="appointments")
    slot = relationship("AvailabilitySlot", back_populates="appointment")


class ImageRequest(Base):
    __tablename__ = "image_requests"
    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    token = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True))
    image_path = Column(String)
    analysis_result = Column(Text)  # JSON string
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
