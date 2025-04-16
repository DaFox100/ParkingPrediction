from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from modules.database import get_garage_data, get_available_dates, get_hourly_aggregate

router = APIRouter(
    prefix="/api",
    tags=["data"]
)

class DataResponse(BaseModel):
    time: str
    value: float

class CombinedDataResponse(BaseModel):
    raw_data: List[DataResponse]
    hourly_values: List[float | None]

@router.get("/data", response_model=CombinedDataResponse)
async def get_data(date: str = None, garage_id: str = "north"):  # Expect YYYY-MM-DD format
    if not date:
        raise HTTPException(
            status_code=400,
            detail="Date parameter is required"
        )
    
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Get raw data from MongoDB
    raw_results = await get_garage_data(date, garage_id)
    
    if not raw_results:
        raise HTTPException(
            status_code=404,
            detail=f"Date {date} not found in available dates"
        )

    # Get hourly aggregated data
    hourly_data = await get_hourly_aggregate(date, garage_id)
    
    if not hourly_data:
        raise HTTPException(
            status_code=404,
            detail=f"Hourly aggregated data not found for date {date}"
        )

    return CombinedDataResponse(
        raw_data=[DataResponse(**result) for result in raw_results],
        hourly_values=hourly_data
    )

@router.get("/dates")
async def get_dates():
    # Get a list of all dates available in the database
    return await get_available_dates()
