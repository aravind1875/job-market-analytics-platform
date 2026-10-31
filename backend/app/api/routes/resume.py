from io import BytesIO
from pathlib import Path
from uuid import uuid4
import zipfile

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Candidate
from app.schemas.resume import ResumeCreate, ResumeResponse
from app.services.candidate_skill_service import (
    extract_and_save_candidate_skills,
)
from app.services.resume_parser import extract_text
from app.services.resume_service import create_resume


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)

UPLOAD_DIR = Path("uploads/resumes")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def validate_file_content(contents: bytes, extension: str) -> None:
    """Validate the uploaded file's basic format before parsing."""

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if extension == ".pdf":
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid PDF file.",
            )
        return

    if extension == ".docx":
        try:
            with zipfile.ZipFile(BytesIO(contents)) as archive:
                members = set(archive.namelist())
                is_valid_docx = (
                    "[Content_Types].xml" in members
                    and "word/document.xml" in members
                )
                if not is_valid_docx:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The uploaded file is not a valid DOCX file.",
                    )
        except zipfile.BadZipFile as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid DOCX file.",
            ) from exc


def remove_uploaded_file(file_path: Path) -> None:
    """Remove a partially processed upload without masking other errors."""
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        # Do not replace the original processing error with a cleanup error.
        pass


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resume_endpoint(
    resume_data: ResumeCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_resume(db, resume_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume_endpoint(
    candidate_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported.",
        )

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} does not exist.",
        )

    # Read at most 1 byte beyond the limit to detect oversized uploads.
    contents = await file.read(MAX_UPLOAD_SIZE + 1)

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The uploaded file exceeds the 10 MB size limit.",
        )

    validate_file_content(contents, extension)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / stored_filename

    try:
        file_path.write_bytes(contents)

        try:
            extracted_text = extract_text(file_path)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded document could not be parsed. Please upload a valid PDF or DOCX file.",
            ) from exc

        resume_data = ResumeCreate(
            candidate_id=candidate_id,
            filename=original_filename,
            file_path=str(file_path),
            extracted_text=extracted_text,
        )

        # Keep resume and extracted skills in the same transaction.
        resume = create_resume(db, resume_data, commit=False)

        extract_and_save_candidate_skills(
            db=db,
            candidate_id=candidate_id,
            resume_text=extracted_text,
        )

        db.commit()
        db.refresh(resume)

        return resume

    except HTTPException:
        db.rollback()
        remove_uploaded_file(file_path)
        raise

    except ValueError as exc:
        db.rollback()
        remove_uploaded_file(file_path)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()
        remove_uploaded_file(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process resume.",
        ) from exc