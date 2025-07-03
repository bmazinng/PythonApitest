# app/models.py
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, ForeignKey
from app.db import Base

class Device(Base):
    __tablename__ = "device"
    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    device_type: Mapped[str] = mapped_column(String)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Patient(Base):
    __tablename__ = "patient"
    patient_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

from sqlalchemy import Index

class HeartRate(Base):
    __tablename__ = "heart_rate"
    __table_args__ = (
        Index("idx_hr_device_time", "device_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, ForeignKey("device.device_id"))
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patient.patient_id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    heart_rate: Mapped[int] = mapped_column(Integer)
    quality: Mapped[str] = mapped_column(String)


class BloodPressure(Base):
    __tablename__ = "blood_pressure"
    __table_args__ = (
        Index("idx_bp_device_time", "device_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, ForeignKey("device.device_id"))
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patient.patient_id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    systolic: Mapped[int] = mapped_column(Integer)
    diastolic: Mapped[int] = mapped_column(Integer)
    pulse: Mapped[int] = mapped_column(Integer)


class DevicePatientAssignment(Base):
    __tablename__ = "device_patient_assignment"
    __table_args__ = (
        Index("idx_assignment_device_patient", "device_id", "patient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String, ForeignKey("device.device_id"))
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patient.patient_id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)