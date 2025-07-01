# app/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Union, List

from app.db import get_db
from app.auth import get_current_device, create_jwt
from app.models import Device, DevicePatientAssignment, HeartRate, BloodPressure
from app.schemas import (
    DeviceRegister, TokenOut, HeartRateInput, HeartRateOut,
    BloodPressureInput, BloodPressureOut
)

router = APIRouter()

@router.post("/register", response_model=TokenOut)
async def register_device(data: DeviceRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.device_id == data.device_id))
    existing = result.scalar_one_or_none()
    if not existing:
        new_device = Device(device_id=data.device_id, device_type=data.device_type)
        db.add(new_device)
        await db.commit()
    token = create_jwt(data.device_id)
    return {"access_token": token}

@router.post("/ingest")
async def ingest_data(
    reading: Union[HeartRateInput, BloodPressureInput],
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    if reading.device_id != device.device_id:
        raise HTTPException(status_code=403, detail="Device ID mismatch")

    assignment_check = await db.execute(
        select(DevicePatientAssignment).where(
            DevicePatientAssignment.device_id == device.device_id,
            DevicePatientAssignment.patient_id == reading.patient_id
        )
    )
    if assignment_check.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Device not assigned to patient")

    try:
        if isinstance(reading, HeartRateInput):
            record = HeartRate(
                device_id=reading.device_id,
                patient_id=reading.patient_id,
                timestamp=reading.timestamp.replace(microsecond=0).replace(tzinfo=None),
                heart_rate=reading.heart_rate,
                quality=reading.measurement_quality,
            )
        else:
            record = BloodPressure(
                device_id=reading.device_id,
                patient_id=reading.patient_id,
                timestamp=reading.timestamp.replace(microsecond=0).replace(tzinfo=None),
                systolic=reading.systolic,
                diastolic=reading.diastolic,
                pulse=reading.pulse,
            )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")
    return {"status": "ok", "id": record.id}

@router.get("/readings/hr", response_model=List[HeartRateOut])
async def get_heart_rate_data(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(HeartRate).where(HeartRate.device_id == device.device_id))
    return result.scalars().all()

@router.get("/readings/bp", response_model=List[BloodPressureOut])
async def get_blood_pressure_data(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BloodPressure).where(BloodPressure.device_id == device.device_id))
    return result.scalars().all()
