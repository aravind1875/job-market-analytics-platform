from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.matching import CandidateMatchResponse
from app.db.database import get_db
from app.db.models import Candidate, Job, Resume
from fastapi import APIRouter, Depends, HTTPException, Query
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
        return calculate_unified_candidate_job_score(
            db=db,
            candidate_id=candidate_id,
            job_id=job_id,
        )

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
