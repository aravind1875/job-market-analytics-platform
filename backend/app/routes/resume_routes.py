from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):

    return {
        "filename": file.filename,
        "message": "Resume uploaded successfully"
    }