
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.logging import logger
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.services.match_history_service import save_match_history
from app.schemas.matching import CandidateMatchResponse
from app.db.database import get_db
from app.db.models import Candidate, Job, JobSkill, Resume, Skill, MatchHistory
from app.services.match_explainer import generate_skill_gap_analysis
from app.services.ats_engine import calculate_ats_score
from app.services.candidate_ranker import (
    calculate_candidate_job_match,
    calculate_unified_candidate_job_score,
    rank_candidates_for_job,
)

router = APIRouter(
    prefix="/matching",
    tags=["Matching"],
)


@router.get("/jobs/{job_id}/candidates/{candidate_id}")
def match_candidate_to_job(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} does not exist",
        )

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {candidate_id} does not exist",
        )

    return calculate_candidate_job_match(
        db=db,
        candidate_id=candidate_id,
        job_id=job_id,
    )

@router.get(
    "/jobs/{job_id}/candidates",
    response_model=list[CandidateMatchResponse],
)
def rank_candidates(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} does not exist",
        )

    return rank_candidates_for_job(
        db=db,
        job_id=job_id,
    )

@router.get("/jobs/{job_id}/candidates/{candidate_id}/ats")
def calculate_candidate_ats(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} does not exist",
        )

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {candidate_id} does not exist",
        )

    resume = (
        db.query(Resume)
        .filter(Resume.candidate_id == candidate_id)
        .order_by(Resume.id.desc())
        .first()
    )

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail=f"No resume found for candidate {candidate_id}",
        )

    if not resume.extracted_text:
        raise HTTPException(
            status_code=400,
            detail=f"Resume for candidate {candidate_id} has no extracted text",
        )



    result = calculate_ats_score(
        resume_text=resume.extracted_text,
        job_description=job.description,
    )

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "resume_id": resume.id,
        "filename": resume.filename,
        **result,
    }

@router.get("/jobs/{job_id}/candidates/{candidate_id}/score")

def calculate_candidate_score(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    try:
        score_result = calculate_unified_candidate_job_score(
            db=db,
            candidate_id=candidate_id,
            job_id=job_id,
        )

        history_record = save_match_history(db, score_result)

        return {
            **score_result,
            "history_id": history_record.id,
            "evaluated_at": history_record.created_at,
        }

    except ValueError as exc:
        message = str(exc)

        if "does not exist" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        if "No resume found" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        if "no extracted text" in message:
            raise HTTPException(
                status_code=400,
                detail=message,
            ) from exc

        raise

    except Exception:
        logger.exception(
            "Unexpected error calculating candidate match score "
            "(job_id=%s, candidate_id=%s)",
            job_id,
            candidate_id,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while calculating the match score.",
        ) from None


@router.get(
    "/jobs/{job_id}/recommendations",
    response_model=list[CandidateMatchResponse],
)
def recommend_candidates(
    job_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    min_score: float = Query(default=0, ge=0, le=100),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} does not exist",
        )

    rankings = rank_candidates_for_job(
        db=db,
        job_id=job_id,
    )

    recommendations = [
        candidate
        for candidate in rankings
        if candidate["overall_score"] >= min_score
        and candidate.get("resume_id") is not None
    ]

    return recommendations[:limit]
@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/skill-gaps"
)
def analyze_candidate_skill_gaps(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    try:
        score_result = calculate_unified_candidate_job_score(
            db=db,
            candidate_id=candidate_id,
            job_id=job_id,
        )
        job_skills = (
            db.query(JobSkill)
            .join(Skill, JobSkill.skill_id == Skill.id)
            .filter(JobSkill.job_id == job_id)
            .all()
        )

        skill_importance = {
            row.skill.name: row.importance
            for row in job_skills
        }

        gap_analysis = generate_skill_gap_analysis(
            matched_skills=score_result["matched_skills"],
            missing_skills=score_result["missing_skills"],
            skill_importance=skill_importance,
        )

        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "overall_score": score_result["overall_score"],
            **gap_analysis,
        }
    except ValueError as exc:
        message = str(exc)

        if "does not exist" in message or "No resume found" in message:
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        if "no extracted text" in message:
            raise HTTPException(
                status_code=400,
                detail=message,
            ) from exc

        raise

    except Exception:
        logger.exception(
            "Unexpected error analyzing candidate skill gaps "
            "(job_id=%s, candidate_id=%s)",
            job_id,
            candidate_id,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while analyzing skill gaps.",
        ) from None

    job_skills = (
        db.query(JobSkill)
        .join(Skill, JobSkill.skill_id == Skill.id)
        .filter(JobSkill.job_id == job_id)
        .all()
    )

    skill_importance = {
        row.skill.name: row.importance
        for row in job_skills
    }
    gap_analysis = generate_skill_gap_analysis(
        matched_skills=score_result["matched_skills"],
        missing_skills=score_result["missing_skills"],
        skill_importance=skill_importance,
    )

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "overall_score": score_result["overall_score"],
        **gap_analysis,
    }
@router.get("/jobs/{job_id}/candidates/{candidate_id}/history")
def get_candidate_match_history(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found",
        )

    job = db.query(Job).filter(
        Job.id == job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    history = (
        db.query(MatchHistory)
        .filter(
            MatchHistory.candidate_id == candidate_id,
            MatchHistory.job_id == job_id,
        )
        .order_by(desc(MatchHistory.created_at))
        .all()
    )

    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "total_evaluations": len(history),
        "history": [
            {
                "history_id": record.id,
                "overall_score": record.overall_score,
                "skill_match_score": record.skill_match_score,
                "ats_score": record.ats_score,
                "semantic_score": record.semantic_score,
                "classification": record.classification,
                "matched_skills": record.matched_skills,
                "missing_skills": record.missing_skills,
                "resume_id": record.resume_id,
                "evaluated_at": record.created_at,
            }
            for record in history
        ],
    }
