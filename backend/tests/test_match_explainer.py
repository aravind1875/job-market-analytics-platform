
from app.services.match_explainer import (
    classify_match_score,
    generate_match_explanation,
    generate_skill_gap_analysis,
)


def test_classify_match_score_thresholds():
    assert classify_match_score(90) == "Excellent Match"
    assert classify_match_score(75) == "Strong Match"
    assert classify_match_score(60) == "Moderate Match"
    assert classify_match_score(45) == "Weak Match"
    assert classify_match_score(20) == "Poor Match"


def test_generate_match_explanation():
    result = generate_match_explanation(
        overall_score=80,
        matched_skills=["Python", "SQL"],
        missing_skills=["Docker"],
        ats_score=75,
        semantic_score=85,
    )

    assert result["classification"] == "Strong Match"
    assert result["ats_score"] == 75
    assert result["semantic_score"] == 85
    assert "Docker" in result["missing_skills"]


def test_skill_gap_prioritizes_important_skills():
    result = generate_skill_gap_analysis(
        matched_skills=["Python"],
        missing_skills=["Docker", "Kubernetes"],
        skill_importance={
            "Docker": 0.8,
            "Kubernetes": 2.5,
        },
    )

    suggestions = result["improvement_suggestions"]

    assert len(suggestions) == 2
    assert suggestions[0]["skill"] == "Kubernetes"
    assert suggestions[0]["priority"] == "high"
    assert suggestions[1]["skill"] == "Docker"
    assert suggestions[1]["priority"] == "low"
