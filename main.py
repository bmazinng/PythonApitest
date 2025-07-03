import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import Base
from app.routes import router

from sqlalchemy import text
from app.db import engine


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medtrack")

RESET_DB = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        if RESET_DB:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        #indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hr_device_time ON heart_rate(device_id, timestamp);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_bp_device_time ON blood_pressure(device_id, timestamp);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_assignment_device_patient ON device_patient_assignment(device_id, patient_id);"))

    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

