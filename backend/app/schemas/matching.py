from pydantic import BaseModel, ConfigDict


class CandidateMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int
    job_id: int

    overall_score: float
    skill_match_score: float
    ats_score: float
    semantic_score: float

    matched_skills: list[str]
    missing_skills: list[str]
    total_required_skills: int

    resume_id: int | None = None
    resume_filename: str | None = None

    rank: int | None = None
    reason: str | None = None