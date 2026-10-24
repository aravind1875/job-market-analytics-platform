
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.job import JobCreate
from app.services.job_service import create_job


def test_create_job_rolls_back_when_skill_extraction_fails():
    db = MagicMock()
    job_data = JobCreate(
        title="Software Engineer",
        company="Example Company",
        description="Python and FastAPI developer",
    )

    with patch(
        "app.services.job_service.extract_and_save_job_skills",
        side_effect=RuntimeError("Skill extraction failed"),
    ):
        with pytest.raises(RuntimeError, match="Skill extraction failed"):
            create_job(db, job_data)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
