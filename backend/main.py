from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Enable CORS
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
#                    allow_headers=["*"], )


class DataPoint(BaseModel):
    time: str
    value: int


@app.get("/api/data", response_model=List[DataPoint])
async def get_data():
    # Generate sample data for the last 24 hours
    data = []

    for hour in range(1, 25):
        time_str = f"{hour:02d}:00"
        value = random.randint(0, 100)  # Random value between 0-100

        data.append({
            "time": time_str,
            "value": value
        })

    return data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
