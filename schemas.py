"""
Database Schemas for Coffee Plant Growth Tracker

Each Pydantic model represents a collection in MongoDB. The collection
name is the lowercase of the class name (e.g., Plant -> "plant").
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class Plant(BaseModel):
    """Coffee plant basic profile
    Collection: plant
    """
    name: str = Field(..., description="Plant name or identifier")
    variety: Optional[str] = Field(None, description="Coffee variety, e.g., Arabica, Robusta")
    sow_date: date = Field(..., description="Date the seed was planted")
    location: Optional[str] = Field(None, description="Where the plant is located")
    notes: Optional[str] = Field(None, description="Freeform notes")


class GrowthLog(BaseModel):
    """Manual growth observations
    Collection: growthlog
    """
    plant_id: str = Field(..., description="Referenced Plant _id as string")
    observed_at: date = Field(..., description="Observation date")
    height_cm: Optional[float] = Field(None, ge=0, description="Height in centimeters")
    leaves_count: Optional[int] = Field(None, ge=0, description="Number of leaves")
    stage: Optional[str] = Field(None, description="Stage: seed, germination, seedling, vegetative, flowering, cherry, harvest")
    notes: Optional[str] = Field(None, description="Notes")


class SensorReading(BaseModel):
    """IoT/live readings
    Collection: sensorreading
    """
    plant_id: str = Field(..., description="Referenced Plant _id as string")
    recorded_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of reading (UTC)")
    temperature_c: Optional[float] = Field(None, description="Ambient temperature Celsius")
    humidity_pct: Optional[float] = Field(None, ge=0, le=100, description="Air humidity %")
    soil_moisture_pct: Optional[float] = Field(None, ge=0, le=100, description="Soil moisture %")
