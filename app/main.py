import os
from datetime import datetime, timedelta
from uuid import uuid4
from dotenv import load_dotenv
import magic


# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt

from app import models, schemas, crud
from app.dependencies import get_db, engine
from fastapi.middleware.cors import CORSMiddleware
from google import genai

models.Base.metadata.create_all(bind=engine)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configure Google Generative AI with API key from environment variable
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

app = FastAPI(
    title="Smart Document Assistant API",
    description="API for uploading documents and asking questions about their content",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:9002").split(","),  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/health", tags=["System"])
def health_check():
    """
    Health Check Endpoint

    Returns a simple status message to confirm the API is running.

    Returns:
        dict: A dictionary with a status message
    """
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


@app.post("/signup", response_model=schemas.Token, tags=["Authentication"])
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    User Registration

    Creates a new user account with the provided email and password.

    Args:
        user_in (UserCreate): User registration information including email and password
        db (Session): Database session dependency

    Returns:
        Token: Access token for the newly created user

    Raises:
        HTTPException: 400 error if the email is already registered
    """
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, user_in.email, user_in.password)
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    User Login

    Authenticates a user and returns an access token.

    The username field in the form should contain the user's email address.

    Args:
        request (Request): FastAPI request object
        form_data (OAuth2PasswordRequestForm): Form containing username (email) and password
        db (Session): Database session dependency

    Returns:
        Token: Access token for the authenticated user

    Raises:
        HTTPException: 400 error if credentials are incorrect
    """
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/upload", response_model=schemas.UploadResponse, tags=["Documents"])

async def upload_file(
        file: UploadFile = File(...),
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Upload Document Endpoint

    Handles the upload of text and PDF documents, extracting their content for later querying.
    Only authenticated users can upload documents, and there are size and type restrictions.

    Args:
        file (UploadFile): The file to be uploaded (must be .txt or .pdf)
        current_user: The authenticated user (from token)
        db (Session): Database session dependency

    Returns:
        UploadResponse: Metadata about the uploaded document including ID and filename

    Raises:
        HTTPException: 
            - 400 error if file type is not supported
            - 400 error if file is too large (>10MB)
            - 400 error if PDF is encrypted
    """

    filename = os.path.basename(file.filename)
    header_bytes = await file.read(2048)
    mime_type = magic.from_buffer(header_bytes, mime=True)


    if mime_type not in ["text/plain", "application/pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    await file.seek(0)
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

        # More robust text extraction with error handling
        text_parts = []
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    # Remove any problematic characters
                    page_text = ''.join(char for char in page_text if ord(char) < 0xD800 or ord(char) > 0xDFFF)
                    text_parts.append(page_text)
            except Exception as e:
                # Log the error if needed
                text_parts.append("")
                continue

        text = "\n".join(text_parts)
    else:
        text = contents.decode("utf-8", errors="ignore")

    save_dir = "/code/uploads"
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

@app.post("/ask", tags=["Questions"])
async def ask_question(
    ask_request: schemas.AskRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask Question About Document

    Asks a question about a previously uploaded document and returns an answer.

    The question is processed against the document's extracted text content.
    Only authenticated users can ask questions, and they can only query their own documents.
    The question and answer are stored in the history for future reference.

    Args:
        ask_request (AskRequest): Contains the document ID and question text
        current_user: The authenticated user (from token)
        db (Session): Database session dependency

    Returns:
        dict: Contains the answer to the question

    Raises:
        HTTPException: 404 error if the document is not found or doesn't belong to the user
    """
    doc = db.query(models.Document).filter_by(id=ask_request.document_id, user_id=current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Use Google Gemini to generate an answer based on the document context
    context = doc.extracted_text[:500]

    if not GENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Google Generative AI API key not configured. Please set the GENAI_API_KEY environment variable."
        )
    client = genai.Client(api_key=GENAI_API_KEY)
    try:
        # modes = genai.list_models()
        response =client.models.generate_content(
    model='gemini-2.0-flash-001', contents=f"""Given this context: {context} 
        Answer this question: {ask_request.question}""")

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts[0] and response.candidates[0].content.parts[0].text:
            answer_text = response.candidates[0].content.parts[0].text
        else:
            answer_text = "Sorry, I was not able to generate an answer based on the provided context."
    except Exception as e:
        # Log the error if needed
        answer_text = f"Error generating response: {str(e)}"
    history = models.QAHistory(
        user=current_user,
        document=doc,
        question=ask_request.question,
        answer=answer_text,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return {"answer": answer_text}


@app.get("/history", response_model=list[schemas.QAHistoryOut], tags=["History"])
def get_history(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get Question-Answer History

    Retrieves the history of questions and answers for the authenticated user.

    Returns all previous questions asked by the user and their corresponding answers,
    ordered by most recent first.

    Args:
        current_user: The authenticated user (from token)
        db (Session): Database session dependency

    Returns:
        list[QAHistoryOut]: List of question-answer history records
    """
    records = (
        db.query(models.QAHistory)
        .filter(models.QAHistory.user_id == current_user.id)
        .order_by(models.QAHistory.created_at.desc())
        .all()
    )
    return records
