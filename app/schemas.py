from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """User registration data"""
    email: EmailStr
    password: str

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123"
            }
        }


class Token(BaseModel):
    """Authentication token"""
    access_token: str
    token_type: str = "bearer"

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class DocumentOut(BaseModel):
    """Document metadata"""
    id: int
    filename: str
    mime_type: str
    file_size: int
    uploaded_at: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "filename": "sample.pdf",
                "mime_type": "application/pdf",
                "file_size": 125360,
                "uploaded_at": "2023-07-15T14:30:00.000Z"
            }
        }


class UploadResponse(DocumentOut):
    """Response after successful document upload"""
    pass


class AskRequest(BaseModel):
    """Question about a document"""
    document_id: int
    question: str

    class Config:
        schema_extra = {
            "example": {
                "document_id": 1,
                "question": "What are the main points in this document?"
            }
        }


class QAHistoryOut(BaseModel):
    """Question-answer history record"""
    id: int
    document_id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "document_id": 1,
                "question": "What are the main points in this document?",
                "answer": "The main points in this document are...",
                "created_at": "2023-07-15T15:30:00.000Z"
            }
        }
