from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from modules.database import get_garage_data, get_available_dates, get_data_per_hour, get_latest_timestamp, get_garage_averages
from fastapi.concurrency import run_in_threadpool
from pathlib import Path
import sys


project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from modules.database import get_garage_data, get_available_dates, get_data_per_hour, get_latest_timestamp, get_current_weather
from data.forecasting.predict_future_times_individual_garage import calculate_prediction



router = APIRouter(
    prefix="/api",
    tags=["data"]
)

# Global variables to store predictions for each garage
north_predictions: List[int] = []
south_predictions: List[int] = []
west_predictions: List[int] = []
south_campus_predictions: List[int] = []

# Global variables to store tomorrow's predictions
north_predictions_tomorrow: List[int] = []
south_predictions_tomorrow: List[int] = []
west_predictions_tomorrow: List[int] = []
south_campus_predictions_tomorrow: List[int] = []

async def update_prediction():
    """Update the global prediction variables with new predictions."""
    global north_predictions, south_predictions, west_predictions, south_campus_predictions
    global north_predictions_tomorrow, south_predictions_tomorrow, west_predictions_tomorrow, south_campus_predictions_tomorrow
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    garage_predictions = await run_in_threadpool(calculate_prediction, today, hours=48)
    
    # Store first 24 hours in current predictions
    north_predictions = garage_predictions[2][:24]
    south_predictions = garage_predictions[0][:24]
    west_predictions = garage_predictions[1][:24]
    south_campus_predictions = garage_predictions[3][:24]
    
    # Store next 24 hours in tomorrow predictions
    north_predictions_tomorrow = garage_predictions[2][24:]
    south_predictions_tomorrow = garage_predictions[0][24:]
    west_predictions_tomorrow = garage_predictions[1][24:]
    south_campus_predictions_tomorrow = garage_predictions[3][24:]

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

@router.get("/latest-update")
async def get_latest_update():
    """
    Get the timestamp of the most recent data update.
    
    Returns:
        dict: Dictionary containing the latest update timestamp
    """
    latest_timestamp = await get_latest_timestamp()
    if latest_timestamp:
        return {"timestamp": latest_timestamp.isoformat()}
    else:
        raise HTTPException(
            status_code=404,
            detail="No data available"
        )

@router.get("/predictions/{garage}")
async def get_predictions(garage: str) -> List[float]:
    """Get predictions for a specific garage."""
    if garage == "north":
        return north_predictions
    elif garage == "south":
        return south_predictions
    elif garage == "west":
        return west_predictions
    elif garage == "south_campus":
        return south_campus_predictions
    else:
        raise HTTPException(status_code=400, detail="Invalid garage name")

@router.get("/predictions-tomorrow/{garage}")
async def get_predictions_tomorrow(garage: str) -> List[float]:
    """Get tomorrow's predictions for a specific garage."""
    if garage == "north":
        return north_predictions_tomorrow
    elif garage == "south":
        return south_predictions_tomorrow
    elif garage == "west":
        return west_predictions_tomorrow
    elif garage == "south_campus":
        return south_campus_predictions_tomorrow
    else:
        raise HTTPException(status_code=400, detail="Invalid garage name")

@router.get("/average-fullness/{garage}/{day}")
async def get_average_fullness(garage: str, day: int) -> List[int]:
    """
    Get average fullness per hour for a specific garage and day of the week.
    
    Args:
        garage (str): Garage name (north, south, west, south_campus)
        day (int): Day of week (0 = Monday, 6 = Sunday)
        
    Returns:
        List[int]: List of 24 integers representing average fullness for each hour
    """
    if day < 0 or day > 6:
        raise HTTPException(status_code=400, detail="Day must be between 0 (Monday) and 6 (Sunday)")
    
    try:
        garage_averages = await get_garage_averages(garage)
        return garage_averages[day]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/weather")
async def get_weather():
    """
    Get current weather data including temperature and condition.
    
    Returns:
        dict: Dictionary containing temperature in Fahrenheit and weather condition
    """
    weather_data = await get_current_weather()
    return weather_data


