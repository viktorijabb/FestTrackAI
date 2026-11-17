from contextlib import asynccontextmanager
from festtrackai.db.database import init_db
# src/festtrackai/main.py
from fastapi import FastAPI
from festtrackai.api.routes import router as festivals_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="FestTrackAI API",
    description="Local-first FilmFreeway data ingestion pipeline",
    version="1.0.0"
)

# Mount the festival router under the expected API prefix
app.include_router(festivals_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
