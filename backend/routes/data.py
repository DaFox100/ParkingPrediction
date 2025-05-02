from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from modules.database import get_garage_data, get_available_dates, get_data_per_hour

router = APIRouter(
    prefix="/api",
    tags=["data"]
)

# Response model that returns the raw data
class DataResponse(BaseModel):
    time: str
    value: float
    
# Response model that returns the raw data and the hourly aggregated data
class CombinedDataResponse(BaseModel):
    raw_data: List[DataResponse]
    hourly_values: List[float | None]

# get_data is the main endpoint for the API
# it returns the raw data and the hourly aggregated data for a given date and garage
# if no date is provided, it returns the data for the latest date
@router.get("/data", response_model=CombinedDataResponse)
async def get_data(date: str = datetime.now().strftime("%Y-%m-%d"), garage_id: str = "north"):  # Expect YYYY-MM-DD format
    
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
    hourly_data = await get_data_per_hour(date, garage_id)
    
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
