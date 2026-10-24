from app.services.candidate_skill_service import (extract_and_save_candidate_skills,)
from pathlib import Path
from uuid import uuid4

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
from app.schemas.resume import ResumeCreate, ResumeResponse
from app.services.resume_parser import extract_text
from app.services.resume_service import create_resume


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


UPLOAD_DIR = Path("uploads/resumes")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


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
    # Validate file extension
    original_filename = file.filename or ""

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported.",
        )

    # Validate candidate
    from app.db.models import Candidate

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} does not exist",
        )

    # Make sure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a unique filename to avoid collisions
    stored_filename = f"{uuid4().hex}{extension}"

    file_path = UPLOAD_DIR / stored_filename

    try:
        # Save uploaded file
        contents = await file.read()
        file_path.write_bytes(contents)

        # Extract text
        extracted_text = extract_text(file_path)

        # Create database record
        resume_data = ResumeCreate(
            candidate_id=candidate_id,
            filename=original_filename,
            file_path=str(file_path),
            extracted_text=extracted_text,
        )

        resume = create_resume(db, resume_data, commit=False)

        extract_and_save_candidate_skills(
            db=db,
            candidate_id=candidate_id,
            resume_text=extracted_text,
        )

        db.commit()
        db.refresh(resume)

        return resume

    except ValueError as exc:
        db.rollback()
        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception:
        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process resume.",
        )