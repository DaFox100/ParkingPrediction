import pandas as pd
import asyncio
from datetime import datetime
from modules.database import Datapoint, init_db, insert_datapoint, close_connection

async def migrate_data():
    # Initialize database
    await init_db()
    
    # Read CSV file
    df = pd.read_csv('data/log.csv')
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Process each row
    for _, row in df.iterrows():
        datapoint = Datapoint(
            timestamp=row['date'],
            metadata="sjparking",
            south_status=int(row['south'] * 100),  # Convert to percentage
            west_status=int(row['west'] * 100),
            north_status=int(row['north'] * 100),
            south_campus_status=int(row['south campus'] * 100)
        )
        await insert_datapoint(datapoint)
    
    print(f"Successfully migrated {len(df)} records to MongoDB")
    await close_connection()

if __name__ == "__main__":
    asyncio.run(migrate_data()) 