from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from modules.database import init_db, init_available_dates, close_connection
from routes.data import router as data_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB and available dates on startup
    await init_db()
    await init_available_dates()
    yield
    # Close MongoDB connection on shutdown
    await close_connection()

app = FastAPI(
    title="Parking Data API",
    description="API for accessing parking data",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_router) # Prefix "/api", tag "data"

@app.get("/")
async def root():
    return {"message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
