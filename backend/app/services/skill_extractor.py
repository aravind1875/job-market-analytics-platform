import re

from app.data.skills import SKILL_TAXONOMY


def normalize_skill(skill: str) -> str:
    """Normalize a skill name for consistent matching."""
    return re.sub(r"\s+", " ", skill.strip().lower())


def extract_skills(text: str) -> list[dict]:
    """
    Extract known skills from text using longest-match-first matching.

    Longer skills take priority over shorter overlapping skills.
    Example:
        "REST API" -> REST API
        "C++"      -> C++
    """

    if not text:
        return []

    normalized_text = normalize_skill(text)

    # Flatten taxonomy while retaining category information.
    skill_entries = []

    for category, skills in SKILL_TAXONOMY.items():
        for skill in skills:
            normalized_skill = normalize_skill(skill)

            skill_entries.append(
                {
                    "name": skill,
                    "normalized_name": normalized_skill,
                    "category": category,
                    "length": len(normalized_skill),
                }
            )

    # Longest skills first.
    skill_entries.sort(
        key=lambda item: item["length"],
        reverse=True,
    )

    extracted = []
    matched_spans: list[tuple[int, int]] = []
    seen: set[str] = set()

    for skill in skill_entries:
        normalized_skill = skill["normalized_name"]

        if normalized_skill in seen:
            continue

        pattern = rf"(?<!\w){re.escape(normalized_skill)}(?!\w)"

        match = re.search(pattern, normalized_text)

        if not match:
            continue

        start, end = match.span()

        # Skip if this match overlaps an already matched longer skill.
        overlaps = any(
            start < existing_end
            and end > existing_start
            for existing_start, existing_end in matched_spans
        )

        if overlaps:
            continue

        matched_spans.append((start, end))
        seen.add(normalized_skill)

        extracted.append(
            {
                "name": skill["name"],
                "normalized_name": normalized_skill,
                "category": skill["category"],
                "confidence": 1.0,
            }
        )

    return extracted