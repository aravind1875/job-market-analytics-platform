
from unittest.mock import MagicMock

import pytest

from app.schemas.resume import ResumeCreate
from app.services.resume_service import create_resume


def test_create_resume_rolls_back_when_commit_fails():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("Database commit failed")

    resume_data = ResumeCreate(
        candidate_id=1,
        filename="resume.pdf",
        file_path="uploads/resumes/resume.pdf",
        extracted_text="Python developer",
    )

    with pytest.raises(RuntimeError, match="Database commit failed"):
        create_resume(db, resume_data)

    db.rollback.assert_called_once()
