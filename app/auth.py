# app/auth.py
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.config import settings
from app.models import Device

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_jwt(device_id: str) -> str:
    payload = {
        "sub": device_id,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    }
    return jwt.encode(
        payload,
        settings.private_key,
        algorithm=settings.JWT_ALGO
    )

def verify_jwt(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.public_key,
            algorithms=[settings.JWT_ALGO]
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_device(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Device:
    device_id = verify_jwt(token)
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=401, detail="Device not registered")
    return device
