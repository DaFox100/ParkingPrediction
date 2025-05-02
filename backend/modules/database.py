from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import os
import asyncio
from pydantic import BaseModel
from bson import ObjectId

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "sjparking"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

collection = db["datapoints"]
hourly_collection = db["hourly_aggregates"]

AVAILABLE_DATES = []

# Mapping of garage identifiers to their status fields
GARAGE_MAPPING = {
    "1": "south_status",
    "south": "south_status",
    "2": "west_status",
    "west": "west_status",
    "3": "north_status",
    "north": "north_status",
    "4": "south_campus_status",
    "south_campus": "south_campus_status"
}

GARAGE_ID_MAPPING = {
    "south": 1,
    "west": 2,
    "north": 3,
    "south_campus": 4
}

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
    global hourly_collection
    global AVAILABLE_DATES
    AVAILABLE_DATES = await hourly_collection.distinct("day")
    
async def get_available_dates() -> List[str]:
    return AVAILABLE_DATES

async def get_datapoint(timestamp: datetime) -> Optional[Datapoint]:
    collection = db["datapoints"]
    query = {"timestamp": timestamp}
    datapoint = await collection.find_one(query)
    if datapoint:
        return Datapoint(**datapoint)
    else:
        return None

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

async def get_garage_data(date: str, garage_id: str) -> List[Dict[str, Any]]:
    """
    Get all datapoints for a specific date with their timestamps and garage status values
    
    Args:
        date (str): Date in YYYY-MM-DD format
        garage_id (str): Garage identifier (can be number or name)
        
    Returns:
        List of dictionaries containing time and garage status value
    """
    collection = db["datapoints"]
    
    # Get the corresponding status field from the mapping
    status_field = GARAGE_MAPPING.get(garage_id.lower())
    if not status_field:
        raise ValueError(f"Invalid garage identifier: {garage_id}")
    
    # Convert date string to datetime object
    query_date = datetime.strptime(date, "%Y-%m-%d")
    
    # Pipeline for MongoDB aggregation
    # $gte: greater than or equal to
    # $lt: less than
    # $project: project the fields to include in the output
    # $sort: sort the results by the time field
    
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": query_date,
                    "$lt": query_date.replace(hour=23, minute=59, second=59)
                },
                "metadata": "sjparking"
            }
        },
        {
            "$project": {
                "time": {
                    "$dateToString": {
                        "format": "%H:%M",
                        "date": "$timestamp"
                    }
                },
                "value": f"${status_field}"
            }
        },
        {
            "$sort": {"time": 1}
        }
    ]
    
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    
    return results

async def _aggregate_hourly_data():
    """
    Aggregate all datapoints into hourly averages and store them in a new collection.
    Each document contains 24 hourly values for a specific day and garage.
    Skips days that are already present in the aggregate collection.
    """
    collection = db["datapoints"]
    hourly_collection = db["hourly_aggregates"]
    
    # First, get all unique dates from datapoints
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
        }
    ]
    cursor = collection.aggregate(pipeline)
    dates = await cursor.to_list(length=None)
    
    # Get all dates that are already in the aggregate collection
    existing_dates = await hourly_collection.distinct("day")
    
    # For each date and garage, aggregate hourly data
    for date_doc in dates:
        date_str = date_doc["_id"]
        
        # Skip if this date is already in the aggregate collection
        if date_str in existing_dates:
            print(f"Skipping {date_str} - already aggregated")
            continue
            
        query_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Process each garage
        for garage_id, status_field in GARAGE_MAPPING.items():
            # Skip duplicate mappings (like "1" and "south" mapping to same field)
            if garage_id.isdigit():
                pipeline = [
                    {
                        "$match": {
                            "timestamp": {
                                "$gte": query_date,
                                "$lt": query_date.replace(hour=23, minute=59, second=59)
                            },
                            "metadata": "sjparking"
                        }
                    },
                    {
                        "$group": {
                            "_id": {
                                "$hour": "$timestamp"
                            },
                            "avg_value": {
                                "$avg": f"${status_field}"
                            }
                        }
                    },
                    {
                        "$sort": {"_id": 1}
                    }
                ]
                
                cursor = collection.aggregate(pipeline)
                hourly_data = await cursor.to_list(length=None)
                
                # Create array of 24 values, filling missing hours with None
                values = [None] * 24
                for hour_data in hourly_data:
                    hour = hour_data["_id"]
                    values[hour] = round(hour_data["avg_value"])
                
                # Create document for this day and garage
                doc = {
                    "day": date_str,
                    "garage_id": int(garage_id) if garage_id.isdigit() else garage_id,
                    "values": values
                }
                
                # Upsert the document
                await hourly_collection.update_one(
                    {"day": date_str, "garage_id": doc["garage_id"]},
                    {"$set": doc},
                    upsert=True
                )

async def get_hourly_aggregate(date: str, garage_id: str) -> List[float | None]:
    """
    Get the hourly aggregated data for a specific date and garage.
    
    Args:
        date (str): Date in YYYY-MM-DD format
        garage_id (str): Garage identifier (can be number or name)
        
    Returns:
        Dictionary containing the hourly aggregated data
    """
    collection = db["hourly_aggregates"]
    
    # Convert garage_id to int if it's a number
    try:
        garage_id = int(garage_id)
    except ValueError:
        garage_id = GARAGE_ID_MAPPING.get(garage_id.lower())
    
    query = {
        "day": date,
        "garage_id": garage_id
    }
    
    result = await collection.find_one(query, {"_id": 0, "values": 1})
    if result:
        return result["values"]
    else:
        return []

# if __name__ == "__main__":
#     async def main():
#         print("Deleting datapoint")
#         collection = db["datapoints"]
#         await collection.delete_one({"_id": ObjectId("67f9dd90623e5d68731498c3")})
#         print("Datapoint deleted")
#     asyncio.run(main())
