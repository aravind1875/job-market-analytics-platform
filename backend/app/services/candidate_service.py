from sqlalchemy.orm import Session

from app.db.models import Candidate
from app.schemas.candidate import CandidateCreate


def create_candidate(
    db: Session,
    candidate_data: CandidateCreate,
) -> Candidate:
    candidate = Candidate(
        full_name=candidate_data.full_name,
        email=candidate_data.email,
        phone=candidate_data.phone,
    )

    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return candidate