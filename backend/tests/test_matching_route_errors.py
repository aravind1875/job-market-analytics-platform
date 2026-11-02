
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app


client = TestClient(app)


@pytest.fixture
def mock_database():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield mock_db
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    ("url", "service_path", "safe_message"),
    [
        (
            "/api/v1/matching/jobs/2/candidates/3/ats",
            "app.api.routes.matching.calculate_ats_score",
            "An unexpected error occurred while calculating the ATS score.",
        ),
        (
            "/api/v1/matching/jobs/2/recommendations",
            "app.api.routes.matching.rank_candidates_for_job",
            "An unexpected error occurred while generating candidate recommendations.",
        ),
    ],
)
def test_matching_routes_hide_unexpected_error_details(
    mock_database,
    url,
    service_path,
    safe_message,
):
    with patch(
        service_path,
        side_effect=RuntimeError("sensitive internal detail"),
    ):
        response = client.get(url)

    assert response.status_code == 500
    assert response.json()["detail"] == safe_message
    assert "sensitive internal detail" not in response.text


def test_history_route_hides_unexpected_error_details(mock_database):
    mock_database.query.side_effect = RuntimeError(
        "sensitive internal detail"
    )

    response = client.get(
        "/api/v1/matching/jobs/2/candidates/3/history"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "An unexpected error occurred while retrieving candidate match history."
    )
    assert "sensitive internal detail" not in response.text
