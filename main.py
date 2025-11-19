import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

from database import db, create_document, get_documents
from schemas import Plant, GrowthLog, SensorReading
from bson import ObjectId

app = FastAPI(title="Coffee Growth Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IdModel(BaseModel):
    id: str


def to_str_id(doc: dict):
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


@app.get("/")
def read_root():
    return {"message": "Coffee Growth Tracker Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# ---------------- Plant Endpoints ----------------
@app.post("/plants", response_model=IdModel)
def create_plant(plant: Plant):
    try:
        plant_dict = plant.model_dump()
        new_id = create_document("plant", plant_dict)
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plants")
def list_plants():
    try:
        docs = get_documents("plant")
        return [to_str_id(doc) for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Growth Logs ----------------
@app.post("/growth-logs", response_model=IdModel)
def create_growth_log(log: GrowthLog):
    try:
        # Validate plant existence if possible
        try:
            _ = ObjectId(log.plant_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid plant_id format")
        new_id = create_document("growthlog", log.model_dump())
        return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/growth-logs")
def list_growth_logs(plant_id: Optional[str] = None):
    try:
        filt = {"plant_id": plant_id} if plant_id else {}
        docs = get_documents("growthlog", filt)
        return [to_str_id(doc) for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Sensor Readings (live) ----------------
@app.post("/sensor-readings", response_model=IdModel)
def ingest_sensor_reading(reading: SensorReading):
    try:
        # ObjectId basic validation
        try:
            _ = ObjectId(reading.plant_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid plant_id format")
        new_id = create_document("sensorreading", reading.model_dump())
        return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sensor-readings/latest")
def latest_sensor_readings(plant_id: str, limit: int = 20):
    try:
        # Most recent readings; if no index, sort in memory
        docs = get_documents("sensorreading", {"plant_id": plant_id})
        docs_sorted = sorted(docs, key=lambda d: d.get("recorded_at", datetime.min), reverse=True)
        return [to_str_id(doc) for doc in docs_sorted[: max(1, min(limit, 200))]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Stats ----------------
@app.get("/stats/plant")
def plant_stats(plant_id: str):
    try:
        logs = get_documents("growthlog", {"plant_id": plant_id})
        readings = get_documents("sensorreading", {"plant_id": plant_id})
        # Compute simple stats
        height_values = [l.get("height_cm") for l in logs if l.get("height_cm") is not None]
        max_height = max(height_values) if height_values else None
        min_height = min(height_values) if height_values else None
        avg_height = sum(height_values) / len(height_values) if height_values else None

        temps = [r.get("temperature_c") for r in readings if r.get("temperature_c") is not None]
        avg_temp = sum(temps) / len(temps) if temps else None

        moist = [r.get("soil_moisture_pct") for r in readings if r.get("soil_moisture_pct") is not None]
        avg_moist = sum(moist) / len(moist) if moist else None

        stages = {}
        for l in logs:
            s = l.get("stage")
            if s:
                stages[s] = stages.get(s, 0) + 1

        return {
            "max_height_cm": max_height,
            "min_height_cm": min_height,
            "avg_height_cm": avg_height,
            "avg_temperature_c": avg_temp,
            "avg_soil_moisture_pct": avg_moist,
            "stages_counts": stages,
            "logs_count": len(logs),
            "readings_count": len(readings),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
