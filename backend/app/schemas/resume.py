from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeBase(BaseModel):
    filename: str
    file_path: str
    extracted_text: str | None = None


class ResumeCreate(ResumeBase):
    candidate_id: int


class ResumeResponse(ResumeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    created_at: datetime
    updated_at: datetime