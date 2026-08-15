def classify_match_score(score: float) -> str:
    """
    Classify a candidate-job match based on the overall score.
    """

    if score >= 85:
        return "Excellent Match"

    if score >= 70:
        return "Strong Match"

    if score >= 55:
        return "Moderate Match"

    if score >= 40:
        return "Weak Match"

    return "Poor Match"


def generate_match_explanation(
    overall_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
    ats_score: float,
    semantic_score: float,
) -> dict:
    """
    Generate an explainable summary of a candidate-job match.
    """

    classification = classify_match_score(
        overall_score
    )

    strengths = sorted(
        matched_skills
    )

    missing = sorted(
        missing_skills
    )

    if overall_score >= 85:
        recommendation = (
            "Excellent candidate alignment. "
            "The candidate strongly matches the "
            "technical requirements of this role."
        )

    elif overall_score >= 70:
        recommendation = (
            "Strong candidate alignment. "
            "The candidate matches most important "
            "requirements, with some skill gaps."
        )

    elif overall_score >= 55:
        recommendation = (
            "Moderate candidate alignment. "
            "The candidate has relevant experience "
            "but several requirements need improvement."
        )

    elif overall_score >= 40:
        recommendation = (
            "Weak candidate alignment. "
            "The candidate has some relevant skills "
            "but significant gaps remain."
        )

    else:
        recommendation = (
            "Poor candidate alignment. "
            "The candidate does not currently match "
            "the majority of the role requirements."
        )

    return {
        "classification": classification,
        "strengths": strengths,
        "missing_skills": missing,
        "recommendation": recommendation,
        "ats_score": ats_score,
        "semantic_score": semantic_score,
    }