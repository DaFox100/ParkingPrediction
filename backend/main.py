from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from modules.database import init_db, init_available_dates, close_connection, _aggregate_hourly_data_for_date, calculate_average_fullness
from routes.data import router as data_router, update_prediction
from datetime import datetime
from asyncio import Event
from modules.database import collection, MOST_RECENT_TIMESTAMP

import warnings
warnings.filterwarnings(
    "ignore",
    message="Skipping variable loading for optimizer",
    category=UserWarning
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = Event()

    async def prediction_updater():
        global MOST_RECENT_TIMESTAMP
        while not stop_event.is_set():
            most_recent = await collection.find_one(sort=[("timestamp", -1)])
            if most_recent and most_recent["timestamp"] != MOST_RECENT_TIMESTAMP:
                MOST_RECENT_TIMESTAMP = most_recent["timestamp"]
                await update_prediction()
            await asyncio.sleep(1)  # Add a small delay to prevent tight looping

    # Initialize MongoDB and available dates on startup
    await init_db()
    await update_prediction()
    await init_available_dates()
    await _aggregate_hourly_data_for_date(datetime.now().strftime("%Y-%m-%d"))
    await calculate_average_fullness()  # Calculate average fullness on startup

    updater_task = asyncio.create_task(prediction_updater())
    try:
        yield
    finally:
        stop_event.set()  # Signal the updater task to stop
        await updater_task  # Wait for the task to finish
        # Close MongoDB connection on shutdown
        await close_connection()

app = FastAPI(
    title="Parking Data API",
    description="API for accessing parking data",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_router) # Prefix "/api", tag "data"

@app.get("/")
async def root():
    return {"message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
