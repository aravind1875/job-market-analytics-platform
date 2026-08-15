from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Candidate,
    CandidateSkill,
    Job,
    JobSkill,
    Resume,
    Skill,
)

from app.services.ats_engine import calculate_ats_score
from app.services.semantic_matcher import (
    calculate_semantic_similarity,
    calculate_batch_semantic_similarity,
)

def calculate_candidate_job_match(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> dict:
    """
    Calculate a weighted skill-match score between a candidate and a job.

    Job skills contribute according to their importance.
    Candidate skill confidence is used as the candidate-side weight.
    """

    candidate_rows = (
        db.query(
            Skill.id,
            Skill.name,
            CandidateSkill.confidence,
        )
        .join(
            CandidateSkill,
            CandidateSkill.skill_id == Skill.id,
        )
        .filter(
            CandidateSkill.candidate_id == candidate_id,
        )
        .all()
    )

    job_rows = (
        db.query(
            Skill.id,
            Skill.name,
            JobSkill.importance,
        )
        .join(
            JobSkill,
            JobSkill.skill_id == Skill.id,
        )
        .filter(
            JobSkill.job_id == job_id,
        )
        .all()
    )

    candidate_skills = {
        row.id: {
            "name": row.name,
            "confidence": (
                row.confidence
                if row.confidence is not None
                else 1.0
            ),
        }
        for row in candidate_rows
    }

    return _calculate_skill_match(
        candidate_id=candidate_id,
        job_id=job_id,
        candidate_skills=candidate_skills,
        job_rows=job_rows,
    )


def _calculate_skill_match(
    candidate_id: int,
    job_id: int,
    candidate_skills: dict,
    job_rows: list,
) -> dict:
    """
    Calculate skill matching using already-loaded data.

    This helper avoids database queries during bulk ranking.
    """

    if not job_rows:
        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "match_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "total_required_skills": 0,
        }

    total_weight = 0.0
    matched_weight = 0.0

    matched_skills = []
    missing_skills = []

    for job_skill in job_rows:
        importance = (
            job_skill.importance
            if job_skill.importance is not None
            else 1.0
        )

        total_weight += importance

        candidate_skill = candidate_skills.get(
            job_skill.skill_id
            if hasattr(job_skill, "skill_id")
            else job_skill.id
        )

        if candidate_skill is not None:
            confidence = candidate_skill["confidence"]

            matched_weight += importance * confidence

            matched_skills.append(
                candidate_skill["name"]
            )
        else:
            missing_skills.append(
                job_skill.name
                if hasattr(job_skill, "name")
                else job_skill.skill.name
            )

    match_score = (
        matched_weight / total_weight * 100
        if total_weight > 0
        else 0.0
    )

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "match_score": round(match_score, 2),
        "matched_skills": sorted(matched_skills),
        "missing_skills": sorted(missing_skills),
        "total_required_skills": len(job_rows),
    }


def calculate_unified_candidate_job_score(
    db: Session,
    candidate_id: int,
    job_id: int,
) -> dict:
    """
    Calculate the overall candidate-job compatibility score.

    Components:
        Skill match: 50%
        ATS score: 30%
        Semantic similarity: 20%
    """

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise ValueError(
            f"Job {job_id} does not exist"
        )

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if candidate is None:
        raise ValueError(
            f"Candidate {candidate_id} does not exist"
        )

    resume = (
        db.query(Resume)
        .filter(
            Resume.candidate_id == candidate_id
        )
        .order_by(Resume.id.desc())
        .first()
    )

    if resume is None:
        raise ValueError(
            f"No resume found for candidate {candidate_id}"
        )

    if not resume.extracted_text:
        raise ValueError(
            f"Resume for candidate {candidate_id} "
            "has no extracted text"
        )

    skill_result = calculate_candidate_job_match(
        db=db,
        candidate_id=candidate_id,
        job_id=job_id,
    )

    ats_result = calculate_ats_score(
        resume_text=resume.extracted_text,
        job_description=job.description,
    )

    semantic_result = calculate_semantic_similarity(
        resume_text=resume.extracted_text,
        job_description=job.description,
    )

    skill_score = skill_result["match_score"]
    ats_score = ats_result["ats_score"]
    semantic_score = semantic_result["semantic_score"]

    overall_score = (
        skill_score * 0.50
        + ats_score * 0.30
        + semantic_score * 0.20
    )

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "overall_score": round(overall_score, 2),
        "skill_match_score": skill_score,
        "ats_score": ats_score,
        "semantic_score": semantic_score,
        "matched_skills": skill_result[
            "matched_skills"
        ],
        "missing_skills": skill_result[
            "missing_skills"
        ],
        "total_required_skills": skill_result[
            "total_required_skills"
        ],
        "resume_id": resume.id,
        "resume_filename": resume.filename,
    }


def _calculate_unified_from_loaded_data(
    candidate: Candidate,
    job: Job,
    semantic_result: dict,
) -> dict:
    """
    Calculate unified score using preloaded SQLAlchemy relationships
    and a precomputed semantic similarity result.

    No database queries or embedding generation are performed here.
    """

    resumes = candidate.resumes

    if not resumes:
        raise ValueError(
            f"No resume found for candidate {candidate.id}"
        )

    resume = max(
        resumes,
        key=lambda item: item.id,
    )

    if not resume.extracted_text:
        raise ValueError(
            f"Resume for candidate {candidate.id} "
            "has no extracted text"
        )

    candidate_skills = {
        candidate_skill.skill_id: {
            "name": candidate_skill.skill.name,
            "confidence": (
                candidate_skill.confidence
                if candidate_skill.confidence is not None
                else 1.0
            ),
        }
        for candidate_skill in candidate.skills
    }

    skill_result = _calculate_skill_match(
        candidate_id=candidate.id,
        job_id=job.id,
        candidate_skills=candidate_skills,
        job_rows=job.skills,
    )

    ats_result = calculate_ats_score(
        resume_text=resume.extracted_text,
        job_description=job.description,
    )

    skill_score = skill_result["match_score"]
    ats_score = ats_result["ats_score"]
    semantic_score = semantic_result["semantic_score"]

    overall_score = (
        skill_score * 0.50
        + ats_score * 0.30
        + semantic_score * 0.20
    )

    return {
        "candidate_id": candidate.id,
        "job_id": job.id,
        "overall_score": round(overall_score, 2),
        "skill_match_score": skill_score,
        "ats_score": ats_score,
        "semantic_score": semantic_score,
        "matched_skills": skill_result[
            "matched_skills"
        ],
        "missing_skills": skill_result[
            "missing_skills"
        ],
        "total_required_skills": skill_result[
            "total_required_skills"
        ],
        "resume_id": resume.id,
        "resume_filename": resume.filename,
    }

def rank_candidates_for_job(
    db: Session,
    job_id: int,
) -> list[dict]:
    """
    Rank all candidates for a given job using the unified score.

    Database relationships are eagerly loaded and semantic embeddings
    are calculated in a single batch.
    """

    job = (
        db.query(Job)
        .options(
            selectinload(Job.skills).selectinload(
                JobSkill.skill
            )
        )
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise ValueError(
            f"Job {job_id} does not exist"
        )

    candidates = (
        db.query(Candidate)
        .options(
            selectinload(Candidate.resumes),
            selectinload(Candidate.skills).selectinload(
                CandidateSkill.skill
            ),
        )
        .order_by(Candidate.id)
        .all()
    )

    rankings = []

    candidates_with_resumes = []
    resume_texts = []

    for candidate in candidates:
        resumes = candidate.resumes

        if not resumes:
            continue

        resume = max(
            resumes,
            key=lambda item: item.id,
        )

        if not resume.extracted_text:
            continue

        candidates_with_resumes.append(
            candidate
        )

        resume_texts.append(
            resume.extracted_text
        )

    semantic_results = calculate_batch_semantic_similarity(
        resume_texts=resume_texts,
        job_description=job.description,
    )

    semantic_by_candidate_id = {
        candidate.id: semantic_result
        for candidate, semantic_result
        in zip(
            candidates_with_resumes,
            semantic_results,
        )
    }

    for candidate in candidates:
        try:
            semantic_result = semantic_by_candidate_id.get(
                candidate.id
            )

            if semantic_result is None:
                raise ValueError(
                    f"No resume found for candidate {candidate.id}"
                )

            result = _calculate_unified_from_loaded_data(
                candidate=candidate,
                job=job,
                semantic_result=semantic_result,
            )

        except ValueError as exc:
            result = {
                "candidate_id": candidate.id,
                "job_id": job_id,
                "overall_score": 0.0,
                "skill_match_score": 0.0,
                "ats_score": 0.0,
                "semantic_score": 0.0,
                "matched_skills": [],
                "missing_skills": [],
                "total_required_skills": 0,
                "reason": str(exc),
            }

        rankings.append(result)

    rankings.sort(
        key=lambda item: item["overall_score"],
        reverse=True,
    )

    for rank, result in enumerate(
        rankings,
        start=1,
    ):
        result["rank"] = rank

    return rankings