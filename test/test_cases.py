import httpx
from datetime import datetime
from rich.console import Console
import time
import asyncio

console = Console()

API_URL = "http://13.60.32.29"

PATIENT_ID = "P001"
DEVICES = [
    {"device_id": "HR001", "device_type": "heart_rate"},
    {"device_id": "BP001", "device_type": "blood_pressure"},
]
TOKENS = {}

async def check_server():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/docs")
            return response.status_code == 200
    except Exception as e:
        console.print(f"[bold red]Server not reachable:[/bold red] {e}")
        return False

async def register_devices():
    async with httpx.AsyncClient() as client:
        for device in DEVICES:
            res = await client.post(f"{API_URL}/register", json=device)
            res.raise_for_status()
            TOKENS[device["device_id"]] = res.json()["access_token"]

async def post_heart_rate():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKENS['HR001']}"}
        payload = {
            "device_id": "HR001",
            "patient_id": PATIENT_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "heart_rate": 75,
            "measurement_quality": "good"
        }
        res = await client.post(f"{API_URL}/ingest", json=payload, headers=headers)
        res.raise_for_status()

async def post_blood_pressure():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKENS['BP001']}"}
        payload = {
            "device_id": "BP001",
            "patient_id": PATIENT_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "systolic": 120,
            "diastolic": 80,
            "pulse": 72
        }
        res = await client.post(f"{API_URL}/ingest", json=payload, headers=headers)
        res.raise_for_status()

async def post_invalid_patient():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKENS['HR001']}"}
        payload = {
            "device_id": "HR001",
            "patient_id": "UNKNOWN",
            "timestamp": datetime.now().isoformat(),
            "heart_rate": 90,
            "measurement_quality": "good"
        }
        res = await client.post(f"{API_URL}/ingest", json=payload, headers=headers)
        if res.status_code != 403:
            raise AssertionError("Expected 403 for unassigned patient.")

async def get_heart_rate():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKENS['HR001']}"}
        res = await client.get(f"{API_URL}/readings/hr", headers=headers)
        res.raise_for_status()

async def get_blood_pressure():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKENS['BP001']}"}
        res = await client.get(f"{API_URL}/readings/bp", headers=headers)
        res.raise_for_status()


async def concurrent_ingestion():
    try:
        hr_task = post_heart_rate()
        bp_task = post_blood_pressure()
        await asyncio.gather(hr_task, bp_task)

    except Exception as e:
        raise AssertionError("Concurrent ingestion failed", e)


async def invalid_token_test():
    headers = {"Authorization": "Bearer invalid_token"}
    res = await httpx.AsyncClient().get(f"{API_URL}/readings/hr", headers=headers)
    if res.status_code != 401:
        raise AssertionError("Invalid token access was not labeled Unathorized")

async def db_timing_test():
    headers = {"Authorization": f"Bearer {TOKENS['BP001']}"}
    start = time.time()
    res = await httpx.AsyncClient().get(f"{API_URL}/readings/hr", headers=headers)
    console.print("DB response time= "+str(time.time() - start))
    res.raise_for_status()

