from collections import defaultdict

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlalchemy import cast, func, select, String
from sqlalchemy.orm import Session
from backend.models import Datapoints, get_db, SessionLocal
from datetime import datetime, date
from typing import List

app = FastAPI()
# Enable CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"], )

AVAILABLE_DATES = []


@app.on_event("startup")
def set_available_dates():
    # Find the list of all available dates in the database and store in global var
    global AVAILABLE_DATES
    with SessionLocal() as db:
        dates = db.query(cast(func.date(Datapoints.timestamp), String).label('date')).distinct().all()
        AVAILABLE_DATES = [date[0] for date in dates]  # YYYY-MM-DD strings


class DataResponse(BaseModel):
    time: str
    value: float


@app.get("/api/data", response_model=List[DataResponse])
async def get_data(date: str = None,  # Expect YYYY-MM-DD format
                   db: Session = Depends(get_db)):
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
        # Check if date exists in cache
    if date not in AVAILABLE_DATES:
        raise HTTPException(
            status_code=404,
            detail=f"Date {date} not found in available dates"
        )

        # Query for specific date's data

    # Query
    results = db.query(Datapoints).filter(
        cast(func.date(Datapoints.timestamp), String) == date).order_by(Datapoints.timestamp).all()

    hourly_sums = defaultdict(lambda: [0,0])



    # Goes to each hour and shifts it up 1 and flattens it out 10:12 -> 11:00 & 10:50 -> 11
    for result in results:
        time_str = result.timestamp.strftime("%H:%M")
        value = result.North_status * 100
        hour = (int(time_str[:2]) + 1) % 24  # Get next hour
        if hour == 0:
            hour = 24
        hour_str = f"{hour:02d}:00"
        hourly_sums[hour_str][0] += value
        hourly_sums[hour_str][1] += 1

    # Construct tuples and append for every hour, calculate sums   Every 11:00 get averaged
    averaged_result = []
    for hour in range(1,25):
        hour_str = f"{hour:02d}:00"
        total, count = hourly_sums[hour_str]
        avg_value = int(total / count if count > 0 else 0)
        averaged_result.append((hour_str, avg_value))

    return [DataResponse(
        time = result[0],
        value = result[1]) for result in averaged_result]



    # return [
    #     {
    #         "time": result.timestamp.strftime("%H:%M"),
    #         "value": result.North_status
    #     }
    #     for result in results
    # ]


@app.get("/api/dates")
async def get_available_dates():
    # Get a list of all dates available in the database
    global AVAILABLE_DATES
    return AVAILABLE_DATES


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
