
from sqlalchemy.orm import Session

from app.db.models import JobSkill, Skill
from app.services.skill_extractor import extract_skills


def extract_and_save_job_skills(
    db: Session,
    job_id: int,
    job_text: str,
) -> list[JobSkill]:
    extracted_skills = extract_skills(job_text)

    saved_skills: list[JobSkill] = []

    for skill_data in extracted_skills:
        skill = (
            db.query(Skill)
            .filter(Skill.normalized_name == skill_data["normalized_name"])
            .first()
        )

        if skill is None:
            skill = Skill(
                name=skill_data["name"],
                normalized_name=skill_data["normalized_name"],
                category=skill_data["category"],
            )
            db.add(skill)
            db.flush()

        existing_job_skill = (
            db.query(JobSkill)
            .filter(
                JobSkill.job_id == job_id,
                JobSkill.skill_id == skill.id,
            )
            .first()
        )

        if existing_job_skill:
            existing_job_skill.importance = skill_data["confidence"]
            saved_skills.append(existing_job_skill)
            continue

        job_skill = JobSkill(
            job_id=job_id,
            skill_id=skill.id,
            importance=skill_data["confidence"],
        )

        db.add(job_skill)
        saved_skills.append(job_skill)

    return saved_skills
