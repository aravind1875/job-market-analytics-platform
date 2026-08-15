from sqlalchemy.orm import Session

from app.db.models import Candidate, CandidateSkill, Skill
from app.services.skill_extractor import extract_skills


def extract_and_save_candidate_skills(
    db: Session,
    candidate_id: int,
    resume_text: str,
) -> list[CandidateSkill]:
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if candidate is None:
        raise ValueError(
            f"Candidate {candidate_id} does not exist"
        )

    extracted_skills = extract_skills(resume_text)

    candidate_skills = []

    for skill_data in extracted_skills:
        skill = (
            db.query(Skill)
            .filter(
                Skill.normalized_name
                == skill_data["normalized_name"]
            )
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

        existing = (
            db.query(CandidateSkill)
            .filter(
                CandidateSkill.candidate_id == candidate_id,
                CandidateSkill.skill_id == skill.id,
            )
            .first()
        )

        if existing:
            existing.confidence = skill_data["confidence"]
            candidate_skills.append(existing)
            continue

        candidate_skill = CandidateSkill(
            candidate_id=candidate_id,
            skill_id=skill.id,
            confidence=skill_data["confidence"],
        )

        db.add(candidate_skill)
        candidate_skills.append(candidate_skill)

    db.commit()

    for candidate_skill in candidate_skills:
        db.refresh(candidate_skill)

    return candidate_skills