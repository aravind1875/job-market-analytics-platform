import re

from app.services.skill_extractor import extract_skills


SECTION_KEYWORDS = {
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "internship",
    ],
    "education": [
        "education",
        "degree",
        "bachelor",
        "master",
        "b.tech",
        "m.tech",
    ],
    "projects": [
        "projects",
        "project",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
    ],
}


def _normalize_text(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


def _calculate_skill_coverage(
    resume_text: str,
    job_description: str,
) -> tuple[float, list[str], list[str]]:
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_description)

    resume_skill_names = {
        skill["normalized_name"]
        for skill in resume_skills
    }

    matched_skills = []
    missing_skills = []

    for skill in job_skills:
        normalized_name = skill["normalized_name"]

        if normalized_name in resume_skill_names:
            matched_skills.append(skill["name"])
        else:
            missing_skills.append(skill["name"])

    total_required = len(job_skills)

    if total_required == 0:
        coverage = 0.0
    else:
        coverage = (
            len(matched_skills) / total_required
        ) * 100

    return (
        round(coverage, 2),
        sorted(set(matched_skills)),
        sorted(set(missing_skills)),
    )


def _calculate_keyword_coverage(
    resume_text: str,
    job_description: str,
) -> float:
    resume_text = _normalize_text(resume_text)
    job_description = _normalize_text(job_description)

    job_words = set(
        re.findall(
            r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b",
            job_description,
        )
    )

    resume_words = set(
        re.findall(
            r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b",
            resume_text,
        )
    )

    if not job_words:
        return 0.0

    matched_words = job_words.intersection(
        resume_words
    )

    return round(
        (len(matched_words) / len(job_words)) * 100,
        2,
    )


def _calculate_structure_score(
    resume_text: str,
) -> tuple[float, list[str]]:
    normalized_text = _normalize_text(resume_text)

    detected_sections = []

    for section, keywords in SECTION_KEYWORDS.items():
        if any(
            keyword in normalized_text
            for keyword in keywords
        ):
            detected_sections.append(section)

    score = min(
        (len(detected_sections) / len(SECTION_KEYWORDS)) * 100,
        100,
    )

    return round(score, 2), detected_sections


def calculate_ats_score(
    resume_text: str,
    job_description: str,
) -> dict:
    """
    Calculate an explainable ATS score for a resume
    against a job description.
    """

    skill_coverage, matched_skills, missing_skills = (
        _calculate_skill_coverage(
            resume_text,
            job_description,
        )
    )

    keyword_coverage = _calculate_keyword_coverage(
        resume_text,
        job_description,
    )

    structure_score, detected_sections = (
        _calculate_structure_score(
            resume_text,
        )
    )

    final_score = (
        skill_coverage * 0.70
        + keyword_coverage * 0.20
        + structure_score * 0.10
    )

    return {
        "ats_score": round(final_score, 2),
        "skill_coverage": skill_coverage,
        "keyword_coverage": keyword_coverage,
        "structure_score": structure_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "detected_sections": detected_sections,
    }