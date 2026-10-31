
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.database import get_db
from app.schemas.candidate import CandidateCreate, CandidateResponse
from app.services.candidate_service import create_candidate


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
    try:
        return create_candidate(db, candidate_data)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception("Unexpected error while creating candidate")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the candidate.",
        ) from None
