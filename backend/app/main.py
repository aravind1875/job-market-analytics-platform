from fastapi import FastAPI
from app.api.routes.job import router as jobs_router
from app.api.routes.candidates import router as candidates_router
from app.db.database import Base, engine
from app.db import models
from app.api.routes.resume import router as resume_router
from app.api.routes.matching import router as matching_router

app = FastAPI(
    title="Job Market Analytics Platform",
    description="AI-powered resume analysis and candidate ranking platform.",
    version="0.1.0",
)

app.include_router(
    candidates_router,
    prefix="/api/v1",
)

app.include_router(
    resume_router,
    prefix="/api/v1",
)

app.include_router(
    jobs_router,
    prefix="/api/v1",
)

app.include_router(
    matching_router,
    prefix="/api/v1",
)

@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Job Market Analytics Platform API",
        "version": "0.1.0",
    }