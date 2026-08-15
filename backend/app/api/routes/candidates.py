from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.candidate import CandidateCreate, CandidateResponse
from app.services.candidate_service import create_candidate
from collections.abc import Generator

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
)


@router.post(
    "",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate_endpoint(
    candidate_data: CandidateCreate,
    db: Session = Depends(get_db),
):
    return create_candidate(db, candidate_data)