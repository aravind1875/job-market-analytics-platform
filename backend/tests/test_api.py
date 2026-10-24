from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import MagicMock, patch
from app.db.database import get_db


client = TestClient(app)


def test_health_check():
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Job Market Analytics Platform API"


def test_matching_routes_are_registered():
    paths = app.openapi()["paths"]

    assert "/api/v1/matching/jobs/{job_id}/candidates/{candidate_id}/score" in paths
    assert "/api/v1/matching/jobs/{job_id}/candidates" in paths
    assert "/api/v1/matching/jobs/{job_id}/recommendations" in paths
    assert "/api/v1/matching/jobs/{job_id}/candidates/{candidate_id}/skill-gaps" in paths
    assert "/api/v1/matching/jobs/{job_id}/candidates/{candidate_id}/history" in paths

def test_score_endpoint_hides_unexpected_error_details():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "app.api.routes.matching.calculate_unified_candidate_job_score",
            side_effect=RuntimeError("sensitive internal detail"),
        ):
            response = client.get(
                "/api/v1/matching/jobs/2/candidates/3/score"
            )

        assert response.status_code == 500
        assert response.json()["detail"] == (
            "An unexpected error occurred while calculating the match score."
        )
        assert "sensitive internal detail" not in response.text
    finally:
        app.dependency_overrides.clear()

def test_score_endpoint_returns_404_for_missing_candidate():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "app.api.routes.matching.calculate_unified_candidate_job_score",
            side_effect=ValueError("Candidate 999 does not exist"),
        ):
            response = client.get(
                "/api/v1/matching/jobs/2/candidates/999/score"
            )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Candidate 999 does not exist"
        )
    finally:
        app.dependency_overrides.clear()
def test_skill_gap_endpoint_hides_unexpected_error_details():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "app.api.routes.matching.calculate_unified_candidate_job_score",
            side_effect=RuntimeError("sensitive internal detail"),
        ):
            response = client.get(
                "/api/v1/matching/jobs/2/candidates/3/skill-gaps"
            )

        assert response.status_code == 500
        assert response.json()["detail"] == (
            "An unexpected error occurred while analyzing skill gaps."
        )
        assert "sensitive internal detail" not in response.text
    finally:
        app.dependency_overrides.clear()