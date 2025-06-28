from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship('Document', back_populates='owner')
    history = relationship('QAHistory', back_populates='user')

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)
    extracted_text = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship('User', back_populates='documents')
    history = relationship('QAHistory', back_populates='document')

class QAHistory(Base):
    __tablename__ = 'qa_history'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    document_id = Column(Integer, ForeignKey('documents.id'))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='history')
    document = relationship('Document', back_populates='history')
