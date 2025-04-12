from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "sjparking"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

AVAILABLE_DATES = []

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
            # Create index on date field for faster queries
            await db.datapoints.create_index([("date", 1)])
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

async def insert_datapoint(data: Dict[str, Any]):
    """
    Insert a new datapoint into the time series collection
    
    Args:
        data (Dict[str, Any]): Dictionary containing the datapoint information
    """

    # TODO This does not insert metadata

    collection = db["datapoints"]
    # Add date field for easier querying
    data["date"] = data["timestamp"].date()
    await collection.insert_one(data)

async def close_connection():
    """Close the MongoDB connection"""
    client.close()

