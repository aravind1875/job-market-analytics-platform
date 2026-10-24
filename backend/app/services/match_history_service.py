
from sqlalchemy.orm import Session

from app.db.models import MatchHistory
from app.services.match_explainer import classify_match_score


def save_match_history(
    db: Session,
    score_result: dict,
) -> MatchHistory:
    """Persist one completed candidate-job scoring evaluation."""

    record = MatchHistory(
        candidate_id=score_result["candidate_id"],
        job_id=score_result["job_id"],
        resume_id=score_result.get("resume_id"),
        overall_score=score_result["overall_score"],
        skill_match_score=score_result["skill_match_score"],
        ats_score=score_result["ats_score"],
        semantic_score=score_result["semantic_score"],
        classification=classify_match_score(
            score_result["overall_score"]
        ),
        matched_skills=score_result["matched_skills"],
        missing_skills=score_result["missing_skills"],
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    return record
