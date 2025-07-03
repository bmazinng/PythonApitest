
from pydantic import BaseModel, Field
from datetime import datetime

class DeviceRegister(BaseModel):
    device_id: str
    device_type: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class HeartRateInput(BaseModel):
    device_id: str
    patient_id: str
    timestamp: datetime
    heart_rate: int = Field(gt=0)
    measurement_quality: str

class HeartRateOut(BaseModel):
    id: int
    device_id: str
    patient_id: str
    timestamp: datetime
    heart_rate: int
    quality: str

class BloodPressureInput(BaseModel):
    device_id: str
    patient_id: str
    timestamp: datetime
    systolic: int
    diastolic: int
    pulse: int

class BloodPressureOut(BaseModel):
    id: int
    device_id: str
    patient_id: str
    timestamp: datetime
    systolic: int
    diastolic: int
    pulse: int
