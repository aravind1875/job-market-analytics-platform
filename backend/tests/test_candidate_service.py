
from unittest.mock import MagicMock

import pytest

from app.schemas.candidate import CandidateCreate
from app.services.candidate_service import create_candidate


def test_create_candidate_rolls_back_when_commit_fails():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("Database commit failed")

    candidate_data = CandidateCreate(
        full_name="Test Candidate",
        email="candidate@example.com",
        phone="1234567890",
    )

    with pytest.raises(RuntimeError, match="Database commit failed"):
        create_candidate(db, candidate_data)

    db.rollback.assert_called_once()
