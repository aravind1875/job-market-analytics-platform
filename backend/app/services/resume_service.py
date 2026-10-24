
from sqlalchemy.orm import Session

from app.db.models import Candidate, Resume
from app.schemas.resume import ResumeCreate


def create_resume(
    db: Session,
    resume_data: ResumeCreate,
    *,
    commit: bool = True,
) -> Resume:
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == resume_data.candidate_id)
        .first()
    )

    if candidate is None:
        raise ValueError(
            f"Candidate {resume_data.candidate_id} does not exist"
        )

    resume = Resume(
        candidate_id=resume_data.candidate_id,
        filename=resume_data.filename,
        file_path=resume_data.file_path,
        extracted_text=resume_data.extracted_text,
    )

    db.add(resume)

    try:
        db.flush()

        if commit:
            db.commit()
            db.refresh(resume)

    except Exception:
        db.rollback()
        raise

    return resume
