from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CandidateCreate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None
    email: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime