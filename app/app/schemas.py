from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentOut(BaseModel):
    id: int
    filename: str
    mime_type: str
    file_size: int
    uploaded_at: datetime

    class Config:
        orm_mode = True


class UploadResponse(DocumentOut):
    pass


class AskRequest(BaseModel):
    document_id: int
    question: str


class QAHistoryOut(BaseModel):
    id: int
    document_id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        orm_mode = True
