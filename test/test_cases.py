import httpx
from datetime import datetime, timedelta
from rich.console import Console
import time
import asyncio

console = Console()

API_URL = "http://127.0.0.1:8000"

PATIENT_ID = "P001"
DEVICES = [
    {"device_id": "HR001", "device_type": "heart_rate"},
    {"device_id": "BP001", "device_type": "blood_pressure"},
    {"device_id": "HRAGRE", "device_type": "heart_rate"},
    {"device_id": "BPAGRE", "device_type": "blood_pressure"},
]

TOKENS = {}

# Known test timestamps
NOW = datetime.utcnow().replace(microsecond=0)
RANGE_START = NOW - timedelta(minutes=5)
RANGE_END = NOW + timedelta(minutes=5)

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

async def post_new_patient():
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {TOKENS['HR001']}"}
        payload = {
            "device_id": "HR001",
            "patient_id": "NEW",
            "timestamp": datetime.now().isoformat(),
            "heart_rate": 90,
            "measurement_quality": "good"
        }
        res = await client.post(f"{API_URL}/ingest", json=payload, headers=headers)
        res.raise_for_status()

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

async def insert_known_hr_values():
    """Insert predictable heart rate readings"""
    headers = {"Authorization": f"Bearer {TOKENS["HRAGRE"]}"}
    values = [60, 70, 80]
    async with httpx.AsyncClient() as client:
        for i, val in enumerate(values):
            payload = {
                "device_id": "HRAGRE",
                "patient_id": PATIENT_ID,
                "timestamp": (NOW - timedelta(seconds=i * 10)).isoformat(),
                "heart_rate": val,
                "measurement_quality": "good"
            }
            await client.post(f"{API_URL}/ingest", json=payload, headers=headers)
    return values

async def insert_known_bp_values():
    """Insert predictable blood pressure readings"""
    headers = {"Authorization": f"Bearer {TOKENS["BPAGRE"]}"}
    values = [
        {"systolic": 120, "diastolic": 80, "pulse": 70},
        {"systolic": 110, "diastolic": 75, "pulse": 65},
        {"systolic": 130, "diastolic": 85, "pulse": 75},
    ]
    async with httpx.AsyncClient() as client:
        for i, val in enumerate(values):
            payload = {
                "device_id": "BPAGRE",
                "patient_id": PATIENT_ID,
                "timestamp": (NOW - timedelta(seconds=i * 10)).isoformat(),
                **val
            }
            await client.post(f"{API_URL}/ingest", json=payload, headers=headers)
    return values


async def validate_hr_aggregates():
    headers = {"Authorization": f"Bearer {TOKENS['HRAGRE']}"}
    expected = {
        "avg": round(sum([60, 70, 80]) / 3),
        "min": 60,
        "max": 80
    }
    async with httpx.AsyncClient() as client:
        for agg, exp_val in expected.items():
            url = (
                f"{API_URL}/readings/hr?"
                f"aggregate={agg}&from_time={RANGE_START.isoformat()}&to_time={RANGE_END.isoformat()}"
            )
            res = await client.get(url, headers=headers)
            res.raise_for_status()
            data_list = res.json()
            target = next((d for d in data_list if d["patient_id"] == PATIENT_ID), None)
            if not target:
                raise AssertionError(f"No data returned for patient {PATIENT_ID} during {agg}")
            if target["heart_rate"] != exp_val:
                raise AssertionError(f"HeartRate {agg} expected {exp_val}, got {target['heart_rate']}")

async def validate_bp_aggregates():
    headers = {"Authorization": f"Bearer {TOKENS['BPAGRE']}"}
    expected = {
        "avg": {
            "systolic": round((120 + 110 + 130) / 3),
            "diastolic": round((80 + 75 + 85) / 3),
            "pulse": round((70 + 65 + 75) / 3),
        },
        "min": {
            "systolic": 110,
            "diastolic": 75,
            "pulse": 65,
        },
        "max": {
            "systolic": 130,
            "diastolic": 85,
            "pulse": 75,
        },
    }
    async with httpx.AsyncClient() as client:
        for agg, expected_vals in expected.items():
            url = (
                f"{API_URL}/readings/bp?"
                f"aggregate={agg}&from_time={RANGE_START.isoformat()}&to_time={RANGE_END.isoformat()}"
            )
            res = await client.get(url, headers=headers)
            res.raise_for_status()
            data_list = res.json()
            target = next((d for d in data_list if d["patient_id"] == PATIENT_ID), None)
            if not target:
                raise AssertionError(f"No data returned for patient {PATIENT_ID} during {agg}")
            for field, expected_val in expected_vals.items():
                if target[field] != expected_val:
                    raise AssertionError(f"BloodPressure {agg} {field} expected {expected_val}, got {target[field]}")
