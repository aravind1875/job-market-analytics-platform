from fastapi import FastAPI

from app.db.database import Base, engine
from app.db import models


app = FastAPI(
    title="Job Market Analytics Platform",
    description="AI-powered resume analysis and candidate ranking platform.",
    version="0.1.0",
)





@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Job Market Analytics Platform API",
        "version": "0.1.0",
    }