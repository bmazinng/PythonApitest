# main.py
import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import insert
from app.models import Device, Patient, DevicePatientAssignment
from app.db import engine, Base
from app.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medtrack")

RESET_DB = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        if RESET_DB:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        # Only create patient; devices will register dynamically
        await conn.execute(insert(Patient), [{"patient_id": "P001", "name": "John Smith"}])
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    #uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

