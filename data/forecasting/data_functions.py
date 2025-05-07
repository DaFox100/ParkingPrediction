
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

from data.forecasting.constants import (
        LOGS_DIRECTORY,
        EVENTS_DIRECTORY 
    )


load_dotenv()
MONGO_URI = os.environ.get("MONGO_URI")


# Load and preprocess log.csv data
def load_data() -> pd.DataFrame:
    data: pd.DataFrame = pd.read_csv(LOGS_DIRECTORY / "log.csv")
    data = data.drop(columns=["Unnamed: 0", "south density", "west density", "north density", "south compus density"])
    print("\n", data.head(), "\n")
    return data

def load_data_from_mongodb(forecast_start: datetime, limit: int = 1000) -> pd.DataFrame:
    client = MongoClient(MONGO_URI)
    db = client["sjparking"]
    collection = db["datapoints"]

    # Get the 1000 most recent datapoints before forecast_start, sorted descending
    cursor = collection.find(
        {"timestamp": {"$lt": forecast_start}, "metadata": "sjparking"}
    ).sort("timestamp", -1).limit(limit)
    docs = list(cursor)
    if not docs:
        raise ValueError("No data loaded from MongoDB for the requested range!")
    # Reverse to chronological order (oldest to newest)
    docs = docs[::-1]
    df = pd.DataFrame(docs)
    # Rename columns to match CSV
    df.rename(columns={
        "timestamp": "date",
        "south_status": "south",
        "west_status": "west",
        "north_status": "north",
        "south_campus_status": "south campus"  # <-- match CSV
    }, inplace=True)
    df = df.drop(columns=["_id", "metadata"])
    # Scale integer columns to 0.00–1.00
    for col in ["south", "west", "north", "south campus"]:
        df[col] = df[col] / 100.0
    # Reorder columns to match CSV
    df = df[["date", "south", "west", "north", "south campus"]]
    print("\nMongoDB data range:", df['date'].min(), "to", df['date'].max(), "\n")
    print("\n", df.head(), "\n")
    return df

# Load the instruction days CSV and prepare it
def add_instruction_days(data: pd.DataFrame) -> pd.DataFrame:
    global extra_long_data
    instruction_days_df: pd.DataFrame = pd.read_csv(f"{LOGS_DIRECTORY}/sjsu_instruction_days.csv")
    instruction_days_df["Date"] = pd.to_datetime(instruction_days_df["Date"]).dt.date
    instruction_days_df.rename(columns={"Instruction_Day": "instruction_day"}, inplace=True)
    # Prepare the log data
    data['date'] = pd.to_datetime(data['date'])
    data['date_only'] = data['date'].dt.date
    # Merge original instruction day flag
    data = pd.merge(data, instruction_days_df, how="left", left_on="date_only", right_on="Date")
    data["instruction_day"] = data["instruction_day"].fillna(False)

    # Add a column for the previous day that maps to the next day's instruction flag
    next_day_instr_df: pd.DataFrame = instruction_days_df.copy()
    next_day_instr_df["Date"] = next_day_instr_df["Date"] - pd.Timedelta(days=1)
    next_day_instr_df.rename(columns={"instruction_day": "next_day_instruction"}, inplace=True)
        # Merge next-day instruction flag
    data = pd.merge(data, next_day_instr_df, how="left", left_on="date_only", right_on="Date")
    data["next_day_instruction"] = data["next_day_instruction"].fillna(False)
    data.drop(columns=["Date_x", "Date_y", "date_only"], inplace=True)
    return data

#cyclical time encodings
# Prepare data for long-term model (includes time encoding features)
def add_cyclical_time_encoding(data: pd.DataFrame) -> pd.DataFrame:
    ts: pd.Series = data['date']
    data['month_sin']       = np.sin(2 * np.pi * ((ts.dt.month - 1) / 12))
    data['month_cos']       = np.cos(2 * np.pi * ((ts.dt.month - 1) / 12))
    data['day_sin']         = np.sin(2 * np.pi * (ts.dt.day / 31))
    data['day_cos']         = np.cos(2 * np.pi * (ts.dt.day / 31))
    data['day_of_week_sin'] = np.sin(2 * np.pi * (ts.dt.dayofweek / 7))
    data['day_of_week_cos'] = np.cos(2 * np.pi * (ts.dt.dayofweek / 7))
    data['hour_sin']        = np.sin(2 * np.pi * (ts.dt.hour / 24))
    data['hour_cos']        = np.cos(2 * np.pi * (ts.dt.hour / 24))
    data['minute_sin']      = np.sin(2 * np.pi * (ts.dt.minute / 60))
    data['minute_cos']      = np.cos(2 * np.pi * (ts.dt.minute / 60))
    return data.copy()

def add_event_impact_features(data: pd.DataFrame) -> pd.DataFrame:
    # Read event data and rename the event type column
    events_df = pd.read_csv(EVENTS_DIRECTORY / "sjsu_home_games.csv", parse_dates=["Time"])
    events_df.rename(columns={"Sport": "event_type"}, inplace=True)

    # Ensure the forecast dates are in datetime and sort both dataframes (required for merge_asof)
    data['date'] = pd.to_datetime(data['date'])
    data.sort_values('date', inplace=True)
    events_df.sort_values('Time', inplace=True)

    # Merge to get the next upcoming event (direction='forward')
    upcoming = pd.merge_asof(
        data,
        events_df[['Time', 'event_type']],
        left_on='date',
        right_on='Time',
        direction='forward'
    )
    # Replace missing upcoming event with a default string
    upcoming['event_type'] = upcoming['event_type'].fillna("-1")
    data['upcoming_event_time'] = upcoming['Time']
    data['upcoming_event_type'] = upcoming['event_type']
    data['time_until_event'] = (data['upcoming_event_time'] - data['date']).dt.total_seconds() / 60
    data['time_until_event'] = data['time_until_event'].fillna(0)

    # Merge to get the last past event (direction='backward')
    past = pd.merge_asof(
        data,
        events_df[['Time', 'event_type']],
        left_on='date',
        right_on='Time',
        direction='backward'
    )
    # Replace missing past event with a default string if needed
    past['event_type'] = past['event_type'].fillna("-1")
    data['past_event_time'] = past['Time']
    data['past_event_type'] = past['event_type']
    data['time_since_event'] = (data['date'] - data['past_event_time']).dt.total_seconds() / 60
    data['time_since_event'] = data['time_since_event'].fillna(0)

    data.drop(columns=['upcoming_event_time', 'past_event_time'], inplace=True)
    return data