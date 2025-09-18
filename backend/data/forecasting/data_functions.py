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
import sqlite3

from data.forecasting.constants import (
        LOGS_DIRECTORY,
        EVENTS_DIRECTORY 
    )

pd.set_option('future.no_silent_downcasting', True)
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")  # <-- Use value from .env file


# Function to establish a connection to the SQLite database
def get_db_connection():
    try:
        conn = sqlite3.connect(f"{LOGS_DIRECTORY}/log.db")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Function to fetch the latest timestamp from the datapoints table
def get_latest_timestamp(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM datapoints")
        latest_timestamp = cursor.fetchone()[0]
        return pd.to_datetime(latest_timestamp) if latest_timestamp else None
    except sqlite3.Error as e:
        print(f"Error fetching latest timestamp: {e}")
        return None

# Load and preprocess log.csv data
def load_data() -> pd.DataFrame:
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    latest_timestamp = get_latest_timestamp(conn)
    if latest_timestamp:
        print(f"Latest timestamp in datapoints: {latest_timestamp}")

    # Read all data from the datapoints table
    try:
        data = pd.read_sql_query("SELECT * FROM datapoints", conn)
        data['date'] = pd.to_datetime(data['date'])

        # Drop unnecessary columns
        columns_to_drop = ['South_Traffic_density', 'West_Traffic_density', 'North_Traffic_density', 'SouthCampus_Traffic_density']
        data.drop(columns=columns_to_drop, inplace=True, errors='ignore')

        # Resample to regular intervals
        data.set_index('date', inplace=True)
        data_resampled = data.resample('10min').mean().interpolate(method='time')

        # Remove large gaps where data is missing
        threshold = 60  # Threshold in minutes
        time_diffs = data_resampled.index.to_series().diff().dt.total_seconds() / 60
        data_cleaned = data_resampled[time_diffs.fillna(0) <= threshold]

    except sqlite3.Error as e:
        print(f"Error reading data from database: {e}")
        data_cleaned = pd.DataFrame()
    finally:
        conn.close()

    return data_cleaned.reset_index()

def load_data_from_mongodb(forecast_start: datetime, limit: int = 100000, resample_interval: str = '10min') -> pd.DataFrame:
    # Connect to SQLite database
    conn = sqlite3.connect(f"{LOGS_DIRECTORY}/log.db")
    cursor = conn.cursor()

    # Ensure the datapoints table exists (if needed)
    cursor.execute('''CREATE TABLE IF NOT EXISTS datapoints (
                        timestamp DATE PRIMARY KEY,
                        South_status REAL,
                        West_status REAL,
                        North_status REAL,
                        SouthCampus_status REAL)''')
    # export_db_to_csv(f"{LOGS_DIRECTORY}/log.csv")
    # Fetch the latest timestamp from the database
    cursor.execute("SELECT MAX(timestamp) FROM datapoints")
    latest_timestamp = cursor.fetchone()[0]

    if latest_timestamp:
        latest_timestamp = pd.to_datetime(latest_timestamp)
        time_difference = (pd.Timestamp.now() - latest_timestamp).total_seconds() / 3600.0

        # Skip update if the last timestamp is within the past hour
        if time_difference <= 1:
            print("Skipping MongoDB update as the last data point is within the past hour.")
            df = pd.read_sql_query("SELECT * FROM datapoints WHERE timestamp <= ?", conn, params=(forecast_start,))
            conn.close()

            # Convert date column to datetime and set as index for resampling
            df.rename(columns={'timestamp': 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'], format='mixed')
            df.set_index('date', inplace=True)
            columns_to_drop = ['South_Traffic_density', 'West_Traffic_density', 'North_Traffic_density', 'SouthCampus_Traffic_density']
            df.drop(columns=columns_to_drop, inplace=True, errors='ignore')

            # Resample to regular intervals, using linear interpolation for missing values
            df_resampled = df.resample(resample_interval).mean().interpolate(method='linear')
            df_resampled = df_resampled.reset_index()
            return df_resampled
    else: 
        latest_timestamp = pd.Timestamp.min  # If no data exists, set to earliest possible timestamp

    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client["sjparking"]
    collection = db["datapoints"]

    # Fetch new data from MongoDB
    cursor_mongo = collection.find(
        {"timestamp": {"$gt": latest_timestamp, "$lte": forecast_start}, "metadata": "sjparking"}
    ).sort("timestamp", 1).limit(limit)
    docs = list(cursor_mongo)

    if docs:
        # Convert MongoDB data to DataFrame
        new_data = pd.DataFrame(docs)
        new_data = new_data.drop(columns=["_id", "metadata"])

        # Scale integer columns to 0.00–1.00
        for col in ["south_status", "west_status", "north_status", "south_campus_status"]:
            new_data[col] = new_data[col] / 100.0
        new_data.rename(columns={'south_campus_status': 'SouthCampus_status'}, inplace=True)
    # Insert new data into SQLite
    if docs:
        new_data.to_sql("datapoints", conn, if_exists="append", index=False)

    # Read all data from SQLite
    df = pd.read_sql_query("SELECT * FROM datapoints WHERE timestamp <= ?", conn, params=(forecast_start,))

    # Convert date column to datetime and set as index for resampling
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
    df.set_index('timestamp', inplace=True)

    # Resample to regular intervals, using linear interpolation for missing values
    df_resampled = df.resample(resample_interval).mean().interpolate(method='time')
    df_resampled = df_resampled.reset_index()

    conn.close()
    columns_to_drop = ['South_Traffic_density', 'West_Traffic_density', 'North_Traffic_density', 'SouthCampus_Traffic_density']
    df_resampled.drop(columns=columns_to_drop, inplace=True, errors='ignore')
    df_resampled.rename(columns={'timestamp': 'date'}, inplace=True)
    print("\nData range (resampled):", df_resampled['date'].min(), "to", df_resampled['date'].max(), "\n")
    print("\n", df_resampled.head(), "\n")

    return df_resampled

# --- Plotting function for resampled data ---
import matplotlib.pyplot as plt

def plot_mongo_data(df):
    plt.figure(figsize=(15, 6))
    for col in ["South_status", "West_status", "North_status", "SouthCampus_status"]:
        plt.plot(df['date'], df[col], label=col)
    plt.xlabel('Date')
    plt.ylabel('Occupancy (normalized)')
    plt.title('Garage Occupancy Over Time (10-min Resampled)')
    plt.legend()
    plt.tight_layout()
    plt.show()

# Load the instruction days CSV and prepare it
def add_instruction_days(data: pd.DataFrame) -> pd.DataFrame:
    # Load instruction days data
    instruction_days_df: pd.DataFrame = pd.read_csv(f"{LOGS_DIRECTORY}/sjsu_instruction_days.csv")

    # Ensure the Date column in instruction_days_df is in datetime format
    instruction_days_df['Date'] = pd.to_datetime(instruction_days_df['Date'])

    # Ensure the forecast dates are in datetime and sort both dataframes (required for merge_asof)
    data['date'] = pd.to_datetime(data['date'])
    data.sort_values('date', inplace=True)
    instruction_days_df.sort_values('Date', inplace=True)

    # Merge to get the next upcoming instruction day (direction='forward')
    upcoming_instruction = pd.merge_asof(
        data,
        instruction_days_df[instruction_days_df['Instruction_Day'] == True],
        left_on='date',
        right_on='Date',
        direction='forward'
    )
    data['time_until_next_instruction'] = (upcoming_instruction['Date'] - data['date']).dt.total_seconds() / 60

    # Merge to get the next upcoming non-instruction day (direction='forward')
    upcoming_non_instruction = pd.merge_asof(
        data,
        instruction_days_df[instruction_days_df['Instruction_Day'] == False],
        left_on='date',
        right_on='Date',
        direction='forward'
    )
    data['time_until_next_non_instruction'] = (upcoming_non_instruction['Date'] - data['date']).dt.total_seconds() / 60

    # Fill missing values with 0 (if any)
    data['time_until_next_instruction'] = data['time_until_next_instruction'].fillna(0)
    data['time_until_next_non_instruction'] = data['time_until_next_non_instruction'].fillna(0)
    return data

#cyclical time encodings
# Prepare data for long-term model (includes time encoding features)
def add_cyclical_time_encoding(data: pd.DataFrame) -> pd.DataFrame:
    ts: pd.Series = data['date']
    data['month_sin']       = np.sin(2 * np.pi * (ts.dt.month / 12))
    data['month_cos']       = np.cos(2 * np.pi * (ts.dt.month / 12))
    data['day_sin']         = np.sin(2 * np.pi * (ts.dt.day / ts.dt.days_in_month))
    data['day_cos']         = np.cos(2 * np.pi * (ts.dt.day / ts.dt.days_in_month))
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

def graph_instruction_day_encodings(data: pd.DataFrame):
    """
    Graphs the instruction day encodings (time until next instruction day and time until next non-instruction day) for the entire dataset.

    Parameters:
        data (pd.DataFrame): DataFrame containing the dataset with instruction day encodings.
    """
    if 'time_until_next_instruction' not in data.columns or 'time_until_next_non_instruction' not in data.columns:
        print("Instruction day encodings are not present in the dataset.")
        return

    plt.figure(figsize=(12, 6))
    plt.plot(data['date'], data['time_until_next_instruction'], label='Time Until Next Instruction Day', color='blue')
    plt.plot(data['date'], data['time_until_next_non_instruction'], label='Time Until Next Non-Instruction Day', color='orange')
    plt.xlabel('Date')
    plt.ylabel('Days')
    plt.title('Instruction Day Encodings Over Time')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# def export_db_to_csv(output_path: str):
#     """
#     Export the SQLite database to a CSV file for inspection.

#     Parameters:
#         output_path (str): The file path where the CSV will be saved.
#     """
#     # Connect to SQLite database
#     conn = sqlite3.connect(f"{LOGS_DIRECTORY}/log.db")

#     # Read all data from the logs table
#     data = pd.read_sql_query("SELECT * FROM datapoints", conn)

#     # Export to CSV
#     data.to_csv(output_path, index=False)

#     conn.close()
#     print(f"Database exported to {output_path}")
