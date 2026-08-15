from sqlalchemy.orm import Session

from app.db.models import CandidateSkill, Skill
from app.services.skill_extractor import extract_skills


def extract_and_save_candidate_skills(
    db: Session,
    candidate_id: int,
    resume_text: str,
) -> list[CandidateSkill]:
    """
    Extract skills from resume text and persist them
    for the specified candidate.
    """

    extracted_skills = extract_skills(resume_text)

    candidate_skills = []

    for extracted_skill in extracted_skills:
        skill = (
            db.query(Skill)
            .filter(
                Skill.normalized_name
                == extracted_skill["normalized_name"]
            )
            .first()
        )

        if skill is None:
            skill = Skill(
                name=extracted_skill["name"],
                normalized_name=extracted_skill["normalized_name"],
                category=extracted_skill["category"],
            )

            db.add(skill)
            db.flush()

        existing_candidate_skill = (
            db.query(CandidateSkill)
            .filter(
                CandidateSkill.candidate_id == candidate_id,
                CandidateSkill.skill_id == skill.id,
            )
            .first()
        )

        if existing_candidate_skill:
            existing_candidate_skill.confidence = extracted_skill[
                "confidence"
            ]
            candidate_skills.append(existing_candidate_skill)
            continue

        candidate_skill = CandidateSkill(
            candidate_id=candidate_id,
            skill_id=skill.id,
            confidence=extracted_skill["confidence"],
        )

        db.add(candidate_skill)
        candidate_skills.append(candidate_skill)

    db.commit()

    for candidate_skill in candidate_skills:
        db.refresh(candidate_skill)

    return candidate_skills