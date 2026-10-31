
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.main import app


client = TestClient(app)
UPLOAD_URL = "/api/v1/resumes/upload"


@pytest.fixture
def upload_context(tmp_path):
    """Provide an isolated database mock and temporary upload directory."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = (
        MagicMock(id=1)
    )

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    with patch(
        "app.api.routes.resume.UPLOAD_DIR",
        tmp_path / "uploads",
    ):
        try:
            yield mock_db, tmp_path / "uploads"
        finally:
            app.dependency_overrides.pop(get_db, None)


def test_upload_rejects_unsupported_extension(upload_context):
    _, upload_dir = upload_context

    response = client.post(
        UPLOAD_URL,
        data={"candidate_id": "1"},
        files={"file": ("resume.txt", b"some text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only PDF and DOCX files are supported."
    )
    assert not upload_dir.exists()


def test_upload_rejects_oversized_file(upload_context):
    _, upload_dir = upload_context
    oversized_content = b"%PDF-" + (
        b"a" * (10 * 1024 * 1024)
    )

    response = client.post(
        UPLOAD_URL,
        data={"candidate_id": "1"},
        files={
            "file": (
                "resume.pdf",
                oversized_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "The uploaded file exceeds the 10 MB size limit."
    )
    assert not upload_dir.exists()


@pytest.mark.parametrize(
    ("filename", "content", "content_type", "expected_detail"),
    [
        (
            "resume.pdf",
            b"This is not a PDF",
            "application/pdf",
            "The uploaded file is not a valid PDF file.",
        ),
        (
            "resume.docx",
            b"This is not a DOCX archive",
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document",
            "The uploaded file is not a valid DOCX file.",
        ),
    ],
)
def test_upload_rejects_invalid_file_content(
    upload_context,
    filename,
    content,
    content_type,
    expected_detail,
):
    _, upload_dir = upload_context

    response = client.post(
        UPLOAD_URL,
        data={"candidate_id": "1"},
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail
    assert not upload_dir.exists()


def test_upload_returns_404_for_missing_candidate(upload_context):
    mock_db, upload_dir = upload_context
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post(
        UPLOAD_URL,
        data={"candidate_id": "999"},
        files={
            "file": (
                "resume.pdf",
                b"%PDF-test",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate 999 does not exist."
    assert not upload_dir.exists()


def test_upload_parser_failure_rolls_back_and_removes_file(
    upload_context,
):
    mock_db, upload_dir = upload_context

    with patch(
        "app.api.routes.resume.extract_text",
        side_effect=RuntimeError("internal parser details"),
    ):
        response = client.post(
            UPLOAD_URL,
            data={"candidate_id": "1"},
            files={
                "file": (
                    "resume.pdf",
                    b"%PDF-test",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "The uploaded document could not be parsed. "
        "Please upload a valid PDF or DOCX file."
    )
    assert "internal parser details" not in response.text
    mock_db.rollback.assert_called_once()
    assert list(upload_dir.iterdir()) == []


def test_upload_success_commits_and_returns_resume(
    upload_context,
):
    mock_db, upload_dir = upload_context

    created_at = datetime.now(timezone.utc)
    resume = MagicMock()
    resume.id = 10
    resume.candidate_id = 1
    resume.filename = "resume.pdf"
    resume.file_path = str(upload_dir / "stored-resume.pdf")
    resume.extracted_text = "Python FastAPI SQL"
    resume.created_at = created_at
    resume.updated_at = created_at

    with (
        patch(
            "app.api.routes.resume.extract_text",
            return_value="Python FastAPI SQL",
        ),
        patch(
            "app.api.routes.resume.create_resume",
            return_value=resume,
        ) as create_resume_mock,
        patch(
            "app.api.routes.resume.extract_and_save_candidate_skills",
            return_value=[],
        ) as skills_mock,
    ):
        response = client.post(
            UPLOAD_URL,
            data={"candidate_id": "1"},
            files={
                "file": (
                    "resume.pdf",
                    b"%PDF-test",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 10
    assert body["candidate_id"] == 1
    assert body["filename"] == "resume.pdf"
    assert body["extracted_text"] == "Python FastAPI SQL"

    create_resume_mock.assert_called_once()
    assert create_resume_mock.call_args.kwargs["commit"] is False
    skills_mock.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(resume)
    mock_db.rollback.assert_not_called()

    stored_files = list(upload_dir.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".pdf"
