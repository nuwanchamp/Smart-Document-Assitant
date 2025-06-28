import os
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt

from . import models, schemas, crud
from .dependencies import get_db, engine

models.Base.metadata.create_all(bind=engine)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Auth utilities

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


@app.post("/signup", response_model=schemas.Token)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, user_in.email, user_in.password)
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/upload", response_model=schemas.UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = os.path.basename(file.filename)
    if not filename.lower().endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    mime = file.content_type
    if filename.lower().endswith(".pdf"):
        from PyPDF2 import PdfReader
        from io import BytesIO

        reader = PdfReader(BytesIO(contents))
        if reader.is_encrypted:
            raise HTTPException(status_code=400, detail="Encrypted PDFs not supported")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = contents.decode("utf-8", errors="ignore")

    save_dir = "uploads"
    os.makedirs(save_dir, exist_ok=True)
    unique_name = f"{uuid4().hex}_{filename}"
    path = os.path.join(save_dir, unique_name)
    with open(path, "wb") as f:
        f.write(contents)

    doc = models.Document(
        owner=current_user,
        filename=filename,
        mime_type=mime,
        file_size=len(contents),
        storage_path=path,
        extracted_text=text,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@app.post("/ask")
async def ask_question(
    request: schemas.AskRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(models.Document).filter_by(id=request.document_id, user_id=current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Placeholder answer logic using simple echo of question and first characters of document
    context = doc.extracted_text[:500]
    answer_text = f"[Mock answer based on '{context[:50]}...']: {request.question}"
    history = models.QAHistory(
        user=current_user,
        document=doc,
        question=request.question,
        answer=answer_text,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return {"answer": answer_text}


@app.get("/history", response_model=list[schemas.QAHistoryOut])
def get_history(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = (
        db.query(models.QAHistory)
        .filter(models.QAHistory.user_id == current_user.id)
        .order_by(models.QAHistory.created_at.desc())
        .all()
    )
    return records
