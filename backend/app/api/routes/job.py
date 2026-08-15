from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.job import JobCreate, JobResponse
from app.services.job_service import create_job


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_endpoint(
    job_data: JobCreate,
    db: Session = Depends(get_db),
):
    return create_job(db, job_data)