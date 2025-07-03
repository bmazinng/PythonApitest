# app/routes.py
from fastapi import APIRouter,Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Union, List
from datetime import datetime

from app.db import get_db
from app.auth import get_current_device, create_jwt
from app.models import Device, DevicePatientAssignment, HeartRate, BloodPressure, Patient
from app.schemas import (
    DeviceRegister, TokenOut, HeartRateInput, HeartRateOut,
    BloodPressureInput, BloodPressureOut
)

router = APIRouter()

@router.post("/register", response_model=TokenOut)
async def register_device(data: DeviceRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.device_id == data.device_id))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Device already registered")

    # Create new device
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

    # Ensure patient exists
    result = await db.execute(select(Patient).where(Patient.patient_id == reading.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        new_patient = Patient(patient_id=reading.patient_id, name="Unnamed")
        db.add(new_patient)
        await db.commit()

    # Ensure assignment exists
    result = await db.execute(
        select(DevicePatientAssignment).where(
            DevicePatientAssignment.device_id == device.device_id,
            DevicePatientAssignment.patient_id == reading.patient_id
        )
    )
    if result.scalar_one_or_none() is None:
        db.add(DevicePatientAssignment(device_id=device.device_id, patient_id=reading.patient_id))
        await db.commit()

    # Proceed with ingestion
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
    db: AsyncSession = Depends(get_db),
    from_time: datetime = Query(default=None),
    to_time: datetime = Query(default=None),
    aggregate: str = Query(default=None, pattern="^(min|max|avg)?$")
):
    if aggregate:
        agg_func = {
            "min": func.min,
            "max": func.max,
            "avg": func.avg
        }[aggregate]

        query = select(
            HeartRate.patient_id,
            agg_func(HeartRate.heart_rate).label("heart_rate")
        ).where(HeartRate.device_id == device.device_id)

        if from_time:
            query = query.where(HeartRate.timestamp >= from_time)
        if to_time:
            query = query.where(HeartRate.timestamp <= to_time)

        query = query.group_by(HeartRate.patient_id)

        result = await db.execute(query)
        rows = result.all()
        return [
            HeartRateOut(
                id=0,
                device_id=device.device_id,
                patient_id=row.patient_id,
                timestamp=datetime.utcnow(),
                heart_rate=row.heart_rate if row.heart_rate else 0,
                quality=aggregate
            ) for row in rows
        ]

    query = select(HeartRate).where(HeartRate.device_id == device.device_id)
    if from_time:
        query = query.where(HeartRate.timestamp >= from_time)
    if to_time:
        query = query.where(HeartRate.timestamp <= to_time)

    result = await db.execute(query)
    return result.scalars().all()



@router.get("/readings/bp", response_model=List[BloodPressureOut])
async def get_blood_pressure_data(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
    from_time: datetime = Query(default=None),
    to_time: datetime = Query(default=None),
    aggregate: str = Query(default=None, pattern="^(min|max|avg)?$")
):
    if aggregate:
        agg_func = {
            "min": func.min,
            "max": func.max,
            "avg": func.avg
        }[aggregate]

        query = select(
            BloodPressure.patient_id,
            agg_func(BloodPressure.systolic).label("systolic"),
            agg_func(BloodPressure.diastolic).label("diastolic"),
            agg_func(BloodPressure.pulse).label("pulse"),
        ).where(BloodPressure.device_id == device.device_id)

        if from_time:
            query = query.where(BloodPressure.timestamp >= from_time)
        if to_time:
            query = query.where(BloodPressure.timestamp <= to_time)

        query = query.group_by(BloodPressure.patient_id)

        result = await db.execute(query)
        rows = result.all()
        return [
            BloodPressureOut(
                id=0,
                device_id=device.device_id,
                patient_id=row.patient_id,
                timestamp=datetime.utcnow(),
                systolic=row.systolic or 0,
                diastolic=row.diastolic or 0,
                pulse=row.pulse or 0
            ) for row in rows
        ]

    query = select(BloodPressure).where(BloodPressure.device_id == device.device_id)
    if from_time:
        query = query.where(BloodPressure.timestamp >= from_time)
    if to_time:
        query = query.where(BloodPressure.timestamp <= to_time)

    result = await db.execute(query)
    return result.scalars().all()
