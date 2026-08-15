from sqlalchemy.orm import Session
from app.services.job_skill_service import extract_and_save_job_skills
from app.db.models import Job
from app.schemas.job import JobCreate


def create_job(
    db: Session,
    job_data: JobCreate,
) -> Job:
    job = Job(
        title=job_data.title,
        company=job_data.company,
        description=job_data.description,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    extract_and_save_job_skills(
        db=db,
        job_id=job.id,
        job_text=job.description,
    )
    
    return job