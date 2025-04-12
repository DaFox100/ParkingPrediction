from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import os
import asyncio
from pydantic import BaseModel

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "sjparking"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

AVAILABLE_DATES = []

class Datapoint(BaseModel):
    timestamp: datetime
    metadata: str
    south_status: int
    west_status: int
    north_status: int
    south_campus_status: int

async def init_db():
    """Initialize the database and create time series collection if it doesn't exist"""
    try:
        # Check if the time series collection exists
        collections = await db.list_collection_names()
        if "datapoints" not in collections:
            # Create time series collection
            await db.create_collection(
                "datapoints",
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "metadata",
                    "granularity": "minutes"
                }
            )
            # Create index on timestamp
            await db.datapoints.create_index([("timestamp", 1)])
    except Exception as e:
        print(f"Error initializing database: {e}")

async def get_database():
    """Get database connection"""
    return db

async def init_available_dates():
    """Initialize the available dates"""
    collection = db["datapoints"]
    pipeline = [
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$timestamp"
                    }
                }
            }
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    cursor = collection.aggregate(pipeline)
    dates = await cursor.to_list(length=None)   
    AVAILABLE_DATES = [doc["_id"] for doc in dates]

    
async def get_available_dates() -> List[str]:
    
    return AVAILABLE_DATES

async def get_datapoint(timestamp: datetime) -> Datapoint:
    collection = db["datapoints"]
    query = {"timestamp": timestamp}
    datapoint = await collection.find_one(query)
    return Datapoint(**datapoint)


async def insert_datapoint(data: Datapoint):
    """
    Insert a new datapoint into the time series collection
    
    Args:
        data (Datapoint): Datapoint object containing the datapoint information
    """
    collection = db["datapoints"]
    await collection.insert_one(data.model_dump())

async def close_connection():
    """Close the MongoDB connection"""
    client.close()

async def get_hourly_data(date: str) -> List[Dict[str, Any]]:
    """
    Get hourly averaged data for a specific date using time series collection
    
    Args:
        date (str): Date in YYYY-MM-DD format
        
    Returns:
        List of dictionaries containing time and value
    """
    collection = db["datapoints"]
    
    # Convert date string to datetime object
    query_date = datetime.strptime(date, "%Y-%m-%d")
    
    # Pipeline for MongoDB aggregation
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": query_date,
                    "$lt": query_date.replace(hour=23, minute=59, second=59)
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$add": [
                        {"$hour": "$timestamp"},
                        1
                    ]
                },
                "total_value": {"$sum": {"$multiply": ["$North_status", 100]}},
                "count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "hour": {
                    "$cond": {
                        "if": {"$eq": ["$_id", 24]},
                        "then": 24,
                        "else": {"$mod": ["$_id", 24]}
                    }
                },
                "avg_value": {
                    "$cond": [
                        {"$eq": ["$count", 0]},
                        0,
                        {"$divide": ["$total_value", "$count"]}
                    ]
                }
            }
        },
        {
            "$sort": {"hour": 1}
        }
    ]
    
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    
    # Format results
    formatted_results = []
    for result in results:
        hour_str = f"{int(result['hour']):02d}:00"
        formatted_results.append({
            "time": hour_str,
            "value": int(result["avg_value"])
        })
    
    return formatted_results


# if __name__ == "__main__":
#     async def main():
#         await init_db()
#         time = datetime.now()
#         datapoint = Datapoint(
#             timestamp=time,
#             metadata="test",
#             north_status=100,
#             south_status=100,
#             west_status=100,
#             south_campus_status=100
#         )
#         await insert_datapoint(datapoint)
#         print(await get_datapoint(time))
#         await close_connection()

#     asyncio.run(main())
