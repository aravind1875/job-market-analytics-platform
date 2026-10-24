
from sqlalchemy.orm import Session

from app.db.models import Job
from app.schemas.job import JobCreate
from app.services.job_skill_service import extract_and_save_job_skills


def create_job(
    db: Session,
    job_data: JobCreate,
) -> Job:
    job = Job(
        title=job_data.title,
        company=job_data.company,
        description=job_data.description,
    )

    try:
        db.add(job)
        db.flush()

        extract_and_save_job_skills(
            db=db,
            job_id=job.id,
            job_text=job.description,
        )

        db.commit()
        db.refresh(job)

    except Exception:
        db.rollback()
        raise

    return job
