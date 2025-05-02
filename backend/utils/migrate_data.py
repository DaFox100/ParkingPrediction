import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import asyncio
from datetime import datetime
from modules.database import Datapoint, init_db, get_database, close_connection, get_datapoint
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LOGS_DIRECTORY = DATA_DIR / "records"

async def migrate_data():
    # Initialize database
    await init_db()
    
    # Read data from CSV
    df = pd.read_csv(LOGS_DIRECTORY / "log.csv")
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Process in batches of 1000
    batch_size = 1000
    total_rows = len(df)
    count = 0
    skipped = 0
    
    print(f"Migrating {total_rows} rows")
    for i in range(total_rows - 1, -1, -batch_size):
        start_idx = max(0, i - batch_size + 1)
        batch = df.iloc[start_idx:i+1]
        batch_datapoints = []
        
        for _, row in batch.iterrows():
            # Check if datapoint already exists
            existing_datapoint = await get_datapoint(row['date'])
            if existing_datapoint:
                skipped += 1
                continue
                
            datapoint = Datapoint(
                timestamp=row['date'],
                metadata="sjparking",
                south_status=int(row['south'] * 100),  # Convert to percentage
                west_status=int(row['west'] * 100),
                north_status=int(row['north'] * 100),
                south_campus_status=int(row['south campus'] * 100)
            )
            batch_datapoints.append(datapoint)
        
        # Insert batch if we have any new datapoints
        if batch_datapoints:
            # Convert to dictionaries for bulk insert
            batch_dicts = [dp.model_dump() for dp in batch_datapoints]
            collection = (await get_database())["datapoints"]
            await collection.insert_many(batch_dicts)
            count += len(batch_datapoints)
        
        # Print progress
        print(f"Migrated: {count}, Skipped: {skipped}")

    print(f"Migration complete. Total migrated: {count}, Total skipped: {skipped}")
    await close_connection()

if __name__ == "__main__":
    asyncio.run(migrate_data())