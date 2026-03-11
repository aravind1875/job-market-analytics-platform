from fastapi import FastAPI
from app.routes.resume_routes import router as resume_router
from app.routes.ranking_routes import router as ranking_router

app = FastAPI(title="Job Market Analytics Platform")

app.include_router(resume_router)
app.include_router(ranking_router)

@app.get("/")
def home():
    return {"message": "Job Market Analytics Platform API"}