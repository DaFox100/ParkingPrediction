from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import create_engine, Column, Datetime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from datetime import datetime
from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent  # Go to backend then to root
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'log.db')}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Datapoints(Base):
    __tablename__ = "datapoints"

    timestamp = Column(Datetime, primary_key=True)
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


