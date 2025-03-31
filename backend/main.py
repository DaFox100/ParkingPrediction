from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Datapoints, get_db
from datetime import datetime

app = FastAPI()

# Enable CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"], )


# TODO Separate DB stuff into a different file


@app.get("/api/data")
async def get_data(date: str = None, db: Session = Depends(get_db)):
    query = db.query(Datapoints)

    if not date:
        return None

    query = query.filter(func.Date(Datapoints.timestamp == date))
    print(query.order_by(Datapoints.timestamp).all())
    return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
