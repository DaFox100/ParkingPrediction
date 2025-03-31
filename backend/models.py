from sqlalchemy import create_engine, Column, DATETIME, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent  # Go to backend then to root
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'log.db')}"

engine = create_engine(DATABASE_URL) # This opens the connection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Interaction
Base = declarative_base()

# This "Datapoints" class utilizes ORM (mapping the SQL database to python object)
class Datapoints(Base):
    __tablename__ = "datapoints"

    timestamp = Column(DATETIME, primary_key=True)
    South_status = Column(Float)
    South_Traffic_density = Column(Float)
    West_status = Column(Float)
    West_Traffic_density = Column(Float)
    North_status = Column(Float)
    North_Traffic_density = Column(Float)
    SouthCampus_status = Column(Float)
    SouthCampus_Traffic_density = Column(Float)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


