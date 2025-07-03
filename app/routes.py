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
    # 1. Check if the device exists
    result = await db.execute(select(Device).where(Device.device_id == data.device_id))
    existing = result.scalar_one_or_none()

    if not existing:
        new_device = Device(device_id=data.device_id, device_type=data.device_type)
        db.add(new_device)
        await db.commit()

    # 2. Ensure the patient exists
    patient_check = await db.execute(select(Patient).where(Patient.patient_id == data.patient_id))
    patient = patient_check.scalar_one_or_none()
    if not patient:
        new_patient = Patient(patient_id=data.patient_id, name="Unnamed")  # Optionally accept name in input
        db.add(new_patient)
        await db.commit()

    # 3. Assign device to patient (if not already assigned)
    assignment_check = await db.execute(
        select(DevicePatientAssignment).where(
            DevicePatientAssignment.device_id == data.device_id,
            DevicePatientAssignment.patient_id == data.patient_id
        )
    )
    if not assignment_check.scalar_one_or_none():
        db.add(DevicePatientAssignment(device_id=data.device_id, patient_id=data.patient_id))
        await db.commit()

    # 4. Create JWT and return
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
        db: AsyncSession = Depends(get_db),
        from_time: datetime = Query(default=None),
        to_time: datetime = Query(default=None),
        aggregate: str = Query(default=None, pattern="^(min|max|avg)?$")
):
    query = select(HeartRate).where(HeartRate.device_id == device.device_id)

    if from_time:
        query = query.where(HeartRate.timestamp >= from_time)
    if to_time:
        query = query.where(HeartRate.timestamp <= to_time)

    if aggregate:
        agg_func = {
            "min": func.min,
            "max": func.max,
            "avg": func.avg
        }[aggregate]

        agg_query = select(
            agg_func(HeartRate.heart_rate).label("heart_rate")
        ).where(HeartRate.device_id == device.device_id)

        if from_time:
            agg_query = agg_query.where(HeartRate.timestamp >= from_time)
        if to_time:
            agg_query = agg_query.where(HeartRate.timestamp <= to_time)

        result = await db.execute(agg_query)
        value = result.scalar()
        return [{
            "id": 0,
            "device_id": device.device_id,
            "patient_id": "",  # unknown in aggregate
            "timestamp": datetime.utcnow(),
            "heart_rate": value if value is not None else 0,
            "quality": aggregate
        }]

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
    query = select(BloodPressure).where(BloodPressure.device_id == device.device_id)

    if from_time:
        query = query.where(BloodPressure.timestamp >= from_time)
    if to_time:
        query = query.where(BloodPressure.timestamp <= to_time)

    if aggregate:
        agg_func = {
            "min": func.min,
            "max": func.max,
            "avg": func.avg
        }[aggregate]

        agg_query = select(
            agg_func(BloodPressure.systolic).label("systolic"),
            agg_func(BloodPressure.diastolic).label("diastolic"),
            agg_func(BloodPressure.pulse).label("pulse"),
        ).where(BloodPressure.device_id == device.device_id)

        if from_time:
            agg_query = agg_query.where(BloodPressure.timestamp >= from_time)
        if to_time:
            agg_query = agg_query.where(BloodPressure.timestamp <= to_time)

        result = await db.execute(agg_query)
        row = result.first()
        return [{
            "id": 0,
            "device_id": device.device_id,
            "patient_id": "",  # unknown in aggregate
            "timestamp": datetime.utcnow(),
            "systolic": row.systolic if row.systolic else 0,
            "diastolic": row.diastolic if row.diastolic else 0,
            "pulse": row.pulse if row.pulse else 0,
        }]

    result = await db.execute(query)
    return result.scalars().all()
