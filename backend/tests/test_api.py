from fastapi.testclient import TestClient

from app.main import app


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
