
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app


client = TestClient(app)


@pytest.fixture
def mock_database():
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    ("url", "payload", "service_path", "safe_message"),
    [
        (
            "/api/v1/candidates",
            {
                "full_name": "Test Candidate",
                "email": "candidate@example.com",
                "phone": "1234567890",
            },
            "app.api.routes.candidates.create_candidate",
            "An unexpected error occurred while creating the candidate.",
        ),
        (
            "/api/v1/jobs",
            {
                "title": "Software Engineer",
                "company": "Example Company",
                "description": "Python and FastAPI developer",
            },
            "app.api.routes.job.create_job",
            "An unexpected error occurred while creating the job.",
        ),
    ],
)
def test_creation_routes_hide_unexpected_errors(
    mock_database,
    url,
    payload,
    service_path,
    safe_message,
):
    with patch(
        service_path,
        side_effect=RuntimeError("sensitive internal detail"),
    ):
        response = client.post(url, json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == safe_message
    assert "sensitive internal detail" not in response.text


@pytest.mark.parametrize(
    ("url", "payload", "service_path"),
    [
        (
            "/api/v1/candidates",
            {
                "full_name": "Test Candidate",
                "email": "candidate@example.com",
                "phone": "1234567890",
            },
            "app.api.routes.candidates.create_candidate",
        ),
        (
            "/api/v1/jobs",
            {
                "title": "Software Engineer",
                "company": "Example Company",
                "description": "Python and FastAPI developer",
            },
            "app.api.routes.job.create_job",
        ),
    ],
)
def test_creation_routes_map_value_errors_to_400(
    mock_database,
    url,
    payload,
    service_path,
):
    with patch(
        service_path,
        side_effect=ValueError("Invalid application data"),
    ):
        response = client.post(url, json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid application data"


def test_candidate_creation_validation_returns_422():
    response = client.post(
        "/api/v1/candidates",
        json={},
    )

    assert response.status_code == 422
