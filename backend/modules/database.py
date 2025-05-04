from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import os
import asyncio
from pydantic import BaseModel
from bson import ObjectId
import pandas as pd

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "sjparking"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

collection = db["datapoints"]
averaged_collection = db["hourly_aggregates"]
prediction_collection = db["predictions"]

AVAILABLE_DATES = []
MOST_RECENT_TIMESTAMP = None

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

GARAGE_NAMES = ["south", "west", "north", "south_campus"]

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

# Global variables to store average fullness per hour for each day of the week
north_avg_fullness = [[] for _ in range(7)]  # 7 days, each containing 24 hours
south_avg_fullness = [[] for _ in range(7)]
west_avg_fullness = [[] for _ in range(7)]
south_campus_avg_fullness = [[] for _ in range(7)]

async def init_db():
    """Initialize the database and create time series collection if it doesn't exist"""
    try:
        global MOST_RECENT_TIMESTAMP
        
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
        
        # Get the most recent timestamp
        most_recent = await collection.find_one(
            sort=[("timestamp", -1)]
        )
        if most_recent:
            MOST_RECENT_TIMESTAMP = most_recent["timestamp"]
        
    except Exception as e:
        print(f"Error initializing database: {e}")

async def get_database():
    """Get database connection"""
    return db

async def init_available_dates():
    global averaged_collection
    global AVAILABLE_DATES
    AVAILABLE_DATES = await averaged_collection.distinct("day")
    
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
    Skips days that are already present and marked as complete in the aggregate collection.
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
    
    # For each date and garage, aggregate hourly data
    for date_doc in dates:
        date_str = date_doc["_id"]
        query_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Process each garage
        for garage_id, status_field in GARAGE_MAPPING.items():
            # Skip duplicate mappings (like "1" and "south" mapping to same field)
            if garage_id.isdigit():
                # Check if document exists and is complete
                existing_doc = await hourly_collection.find_one({
                    "day": date_str,
                    "garage_id": int(garage_id) if garage_id.isdigit() else garage_id
                })
                
                if existing_doc and existing_doc["complete"] is True:
                    print(f"Skipping {date_str} for garage {garage_id} - already complete")
                    continue
                
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
                
                # Check if all hours have data
                if (values[23] is not None):
                    is_complete = True
                else:
                    is_complete = False
                
                # Create document for this day and garage
                doc = {
                    "day": date_str,
                    "garage_id": int(garage_id) if garage_id.isdigit() else garage_id,
                    "values": values,
                    "complete": is_complete
                }
                
                # Upsert the document
                await hourly_collection.update_one(
                    {"day": date_str, "garage_id": doc["garage_id"]},
                    {"$set": doc},
                    upsert=True
                )

async def get_data_per_hour(date: str, garage_id: str) -> List[float | None]:
    """
    Get the hourly aggregated data for a specific date and garage.
    Checks for new data and re-aggregates if new datapoints are found.
    
    Args:
        date (str): Date in YYYY-MM-DD format
        garage_id (str): Garage identifier (can be number or name)
        
    Returns:
        List containing the hourly aggregated data
    """
    global MOST_RECENT_TIMESTAMP
    
    # Check for new data
    most_recent = await collection.find_one(
        sort=[("timestamp", -1)]
    )
    
    if most_recent and most_recent["timestamp"] != MOST_RECENT_TIMESTAMP:
        # New data found, update the global timestamp
        MOST_RECENT_TIMESTAMP = most_recent["timestamp"]
        
        # Get the date of the new data
        new_date = MOST_RECENT_TIMESTAMP.strftime("%Y-%m-%d")
        
        # Delete existing aggregated data for this date
        await averaged_collection.delete_many({"day": new_date})
        
        # Re-aggregate the data for this date
        await _aggregate_hourly_data_for_date(new_date)
        print(f"Aggregated data for {new_date}")
    
    # Convert garage_id to int if it's a number
    try:
        garage_id = int(garage_id)
    except ValueError:
        garage_id = GARAGE_ID_MAPPING.get(garage_id.lower())
    
    query = {
        "day": date,
        "garage_id": garage_id
    }
    
    result = await averaged_collection.find_one(query, {"_id": 0, "values": 1})
    if result:
        return result["values"]
    else:
        return []

async def _aggregate_hourly_data_for_date(date_str: str):
    """
    Aggregate hourly data for a specific date.
    
    Args:
        date_str (str): Date in YYYY-MM-DD format
    """
    collection = db["datapoints"]
    hourly_collection = db["hourly_aggregates"]
    
    query_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Process each garage
    for garage_id, status_field in GARAGE_MAPPING.items():
        # Skip duplicate mappings (like "1" and "south" mapping to same field)
        if garage_id.isdigit():
            # Convert garage_id to int for storage
            garage_id_int = int(garage_id)
            
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
            
            # Check if all hours have data
            is_complete = values[23] is not None
            
            # Create document for this day and garage
            doc = {
                "day": date_str,
                "garage_id": garage_id_int,
                "values": values,
                "complete": is_complete
            }
            
            # Delete any existing document for this day and garage
            await hourly_collection.delete_one({
                "day": date_str,
                "garage_id": garage_id_int
            })
            
            # Insert the new document
            await hourly_collection.insert_one(doc)
            
            print(f"Aggregated data for {date_str} - Garage {garage_id_int}: {values}")

# if __name__ == "__main__":
#     async def main():
#         print("Deleting datapoint")
#         collection = db["datapoints"]
#         await collection.delete_one({"_id": ObjectId("67f9dd90623e5d68731498c3")})
#         print("Datapoint deleted")
#     asyncio.run(main())



async def get_latest_timestamp() -> datetime:
    """
    Get the most recent timestamp from the database.
    
    Returns:
        datetime: The most recent timestamp
    """
    global MOST_RECENT_TIMESTAMP
    return MOST_RECENT_TIMESTAMP

async def calculate_average_fullness():
    """
    Calculate average fullness per hour for each day of the week for all garages.
    Excludes December, June, and July data.
    Skips weeks where Monday's South Garage data doesn't reach 70% fullness.
    """
    global north_avg_fullness, south_avg_fullness, west_avg_fullness, south_campus_avg_fullness
    
    # Reset the global variables
    north_avg_fullness = [[] for _ in range(7)]
    south_avg_fullness = [[] for _ in range(7)]
    west_avg_fullness = [[] for _ in range(7)]
    south_campus_avg_fullness = [[] for _ in range(7)]
    
    # Get all documents from hourly_aggregates collection
    cursor = averaged_collection.find({"complete": True})
    documents = await cursor.to_list(length=None)
    
    print(f"Checking {len(documents)} documents")
    
    # Group documents by week
    weeks = {}
    for doc in documents:
        date = datetime.strptime(doc["day"], "%Y-%m-%d")
        month = date.month
        
        # Skip December, June, and July
        if month in [6, 7, 12]:
            continue
            
        # Get the start of the week (Monday)
        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].append(doc)
    
    # Keep track of included documents for counting
    included_documents = []
    
    # Process each week
    for week_docs in weeks.values():
        # Check if this week should be included
        should_include_week = False
        
        # Find Monday's South Garage data
        for doc in week_docs:
            date = datetime.strptime(doc["day"], "%Y-%m-%d")
            if date.weekday() == 0 and doc["garage_id"] == 1:  # Monday and South Garage
                values = doc["values"]
                if any(value is not None and value >= 70 for value in values):
                    should_include_week = True
                    break
        
        if not should_include_week:
            continue
        
        # Add all documents from this week to included_documents
        included_documents.extend(week_docs)
        
        # Process documents for this week
        for doc in week_docs:
            date = datetime.strptime(doc["day"], "%Y-%m-%d")
            day_of_week = date.weekday()
            garage_id = doc["garage_id"]
            values = doc["values"]
            
            # Initialize lists for this day if not already done
            if not north_avg_fullness[day_of_week]:
                north_avg_fullness[day_of_week] = [0] * 24
            if not south_avg_fullness[day_of_week]:
                south_avg_fullness[day_of_week] = [0] * 24
            if not west_avg_fullness[day_of_week]:
                west_avg_fullness[day_of_week] = [0] * 24
            if not south_campus_avg_fullness[day_of_week]:
                south_campus_avg_fullness[day_of_week] = [0] * 24
            
            # Add values to appropriate garage's list
            if garage_id == 1:  # South
                for i, value in enumerate(values):
                    if value is not None:
                        south_avg_fullness[day_of_week][i] += value
            elif garage_id == 2:  # West
                for i, value in enumerate(values):
                    if value is not None:
                        west_avg_fullness[day_of_week][i] += value
            elif garage_id == 3:  # North
                for i, value in enumerate(values):
                    if value is not None:
                        north_avg_fullness[day_of_week][i] += value
            elif garage_id == 4:  # South Campus
                for i, value in enumerate(values):
                    if value is not None:
                        south_campus_avg_fullness[day_of_week][i] += value
    
    print(f"Calculating averages")
    print(f"Total included documents: {len(included_documents)}")
    
    # Calculate averages for each garage using only included documents
    for day in range(7):
        # Count number of documents for each day from included documents
        north_count = len([d for d in included_documents if datetime.strptime(d["day"], "%Y-%m-%d").weekday() == day and d["garage_id"] == 3])
        south_count = len([d for d in included_documents if datetime.strptime(d["day"], "%Y-%m-%d").weekday() == day and d["garage_id"] == 1])
        west_count = len([d for d in included_documents if datetime.strptime(d["day"], "%Y-%m-%d").weekday() == day and d["garage_id"] == 2])
        south_campus_count = len([d for d in included_documents if datetime.strptime(d["day"], "%Y-%m-%d").weekday() == day and d["garage_id"] == 4])
        
        print(f"Day {day} counts - North: {north_count}, South: {south_count}, West: {west_count}, South Campus: {south_campus_count}")
        
        # Calculate averages
        if north_count > 0:
            north_avg_fullness[day] = [round(x / north_count) for x in north_avg_fullness[day]]
        if south_count > 0:
            south_avg_fullness[day] = [round(x / south_count) for x in south_avg_fullness[day]]
        if west_count > 0:
            west_avg_fullness[day] = [round(x / west_count) for x in west_avg_fullness[day]]
        if south_campus_count > 0:
            south_campus_avg_fullness[day] = [round(x / south_campus_count) for x in south_campus_avg_fullness[day]]
    
    print(f"Averages calculated")
    print(f"North: {north_avg_fullness[0]}")
    print(f"South: {south_avg_fullness[0]}")
    print(f"West: {west_avg_fullness[0]}")
    print(f"South Campus: {south_campus_avg_fullness[0]}")

async def main():
    await calculate_average_fullness()
    
if __name__ == "__main__":
    asyncio.run(main())

async def get_garage_averages(garage: str) -> List[List[int]]:
    """
    Get the average fullness data for a specific garage.
    
    Args:
        garage (str): Garage name (north, south, west, south_campus)
        
    Returns:
        List[List[int]]: List of 7 lists (one for each day) containing 24 hourly averages
    """
    if garage == "north":
        return north_avg_fullness
    elif garage == "south":
        return south_avg_fullness
    elif garage == "west":
        return west_avg_fullness
    elif garage == "south_campus":
        return south_campus_avg_fullness
    else:
        raise ValueError(f"Invalid garage name: {garage}")