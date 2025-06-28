import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Configure a temporary SQLite database for testing
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['JWT_SECRET_KEY'] = 'test_secret_key'

# Add the app-bkp directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.main import (
    app, 
    create_access_token, 
    get_current_user, 
    health_check, 
    signup, 
    login, 
    upload_file, 
    ask_question, 
    get_history,
    SECRET_KEY,
    ALGORITHM
)
from app.dependencies import engine
from app import models, schemas, crud

# Create the test database tables
models.Base.metadata.create_all(bind=engine)

# Create a test client
client = TestClient(app)


def teardown_module(module):
    """Clean up after tests"""
    try:
        os.remove('test.db')
    except FileNotFoundError:
        pass


class TestHealthCheck:
    def test_health_check(self):
        """Test the health check endpoint returns OK status"""
        response = health_check()
        assert response == {"status": "ok"}


class TestCreateAccessToken:
    def test_create_access_token_with_default_expiry(self):
        """Test creating an access token with default expiry"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        # Decode the token to verify its contents
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Test creating an access token with custom expiry"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        # Decode the token to verify its contents
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload


class TestGetCurrentUser:
    @patch("app.crud.get_user_by_email")
    def test_get_current_user_valid_token(self, mock_get_user):
        """Test getting current user with a valid token"""
        # Create a mock user
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_get_user.return_value = mock_user

        # Create a valid token
        token = create_access_token({"sub": "test@example.com"})

        # Mock the database session
        mock_db = MagicMock()

        # Call the function
        user = get_current_user(db=mock_db, token=token)

        # Verify the result
        assert user == mock_user
        mock_get_user.assert_called_once_with(mock_db, email="test@example.com")

    @patch("app.crud.get_user_by_email")
    def test_get_current_user_invalid_token(self, mock_get_user):
        """Test getting current user with an invalid token"""
        # Create an invalid token (expired)
        expired_delta = timedelta(minutes=-10)  # Token expired 10 minutes ago
        token = create_access_token({"sub": "test@example.com"}, expired_delta)

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            get_current_user(db=mock_db, token=token)

        # Verify the exception
        assert excinfo.value.status_code == 401
        assert "Could not validate credentials" in excinfo.value.detail

        # Verify the mock was not called
        mock_get_user.assert_not_called()

    @patch("app.crud.get_user_by_email")
    def test_get_current_user_user_not_found(self, mock_get_user):
        """Test getting current user when user is not found in database"""
        # Set up the mock to return None (user not found)
        mock_get_user.return_value = None

        # Create a valid token
        token = create_access_token({"sub": "test@example.com"})

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            get_current_user(db=mock_db, token=token)

        # Verify the exception
        assert excinfo.value.status_code == 401
        assert "Could not validate credentials" in excinfo.value.detail

        # Verify the mock was called
        mock_get_user.assert_called_once_with(mock_db, email="test@example.com")


class TestSignup:
    @patch("app.crud.get_user_by_email")
    @patch("app.crud.create_user")
    def test_signup_success(self, mock_create_user, mock_get_user):
        """Test successful user signup"""
        # Set up the mocks
        mock_get_user.return_value = None  # User doesn't exist yet

        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_create_user.return_value = mock_user

        # Create a user request
        user_in = schemas.UserCreate(email="test@example.com", password="password123")

        # Mock the database session
        mock_db = MagicMock()

        # Call the function
        result = signup(user_in=user_in, db=mock_db)

        # Verify the result
        assert "access_token" in result
        assert result["token_type"] == "bearer"

        # Verify the mocks were called correctly
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")
        mock_create_user.assert_called_once_with(mock_db, "test@example.com", "password123")

    @patch("app.crud.get_user_by_email")
    def test_signup_email_already_registered(self, mock_get_user):
        """Test signup with an already registered email"""
        # Set up the mock to return an existing user
        mock_user = MagicMock()
        mock_get_user.return_value = mock_user

        # Create a user request
        user_in = schemas.UserCreate(email="test@example.com", password="password123")

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            signup(user_in=user_in, db=mock_db)

        # Verify the exception
        assert excinfo.value.status_code == 400
        assert "Email already registered" in excinfo.value.detail

        # Verify the mock was called
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")


class TestLogin:
    @patch("app.crud.get_user_by_email")
    @patch("app.crud.verify_password")
    def test_login_success(self, mock_verify_password, mock_get_user):
        """Test successful login"""
        # Set up the mocks
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        mock_get_user.return_value = mock_user

        mock_verify_password.return_value = True

        # Create a form data mock
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "password123"

        # Mock the database session
        mock_db = MagicMock()

        # Call the function
        result = login(form_data=form_data, db=mock_db)

        # Verify the result
        assert "access_token" in result
        assert result["token_type"] == "bearer"

        # Verify the mocks were called correctly
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")
        mock_verify_password.assert_called_once_with("password123", "hashed_password")

    @patch("app.crud.get_user_by_email")
    def test_login_user_not_found(self, mock_get_user):
        """Test login with non-existent user"""
        # Set up the mock to return None (user not found)
        mock_get_user.return_value = None

        # Create a form data mock
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "password123"

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            login(form_data=form_data, db=mock_db)

        # Verify the exception
        assert excinfo.value.status_code == 400
        assert "Incorrect username or password" in excinfo.value.detail

        # Verify the mock was called
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")

    @patch("app.crud.get_user_by_email")
    @patch("app.crud.verify_password")
    def test_login_incorrect_password(self, mock_verify_password, mock_get_user):
        """Test login with incorrect password"""
        # Set up the mocks
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        mock_get_user.return_value = mock_user

        mock_verify_password.return_value = False  # Password verification fails

        # Create a form data mock
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "wrong_password"

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            login(form_data=form_data, db=mock_db)

        # Verify the exception
        assert excinfo.value.status_code == 400
        assert "Incorrect username or password" in excinfo.value.detail

        # Verify the mocks were called correctly
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")
        mock_verify_password.assert_called_once_with("wrong_password", "hashed_password")


class TestUploadFile:
    @pytest.mark.anyio
    @patch("os.makedirs")
    @patch("os.path.join")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("uuid.uuid4")
    async def test_upload_text_file(self, mock_uuid4, mock_open, mock_join, mock_makedirs):
        """Test uploading a text file"""
        # Set up the mocks
        mock_uuid4.return_value = MagicMock(hex="test_uuid")
        mock_join.return_value = "uploads/test_uuid_test.txt"

        # Create a mock file
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"

        # Create a mock that returns a coroutine when called
        mock_read = MagicMock()
        mock_read.return_value = b"test content"

        # Make the mock awaitable
        mock_file.read = AsyncMock(return_value=b"test content")

        # Create a mock user
        mock_user = MagicMock()
        mock_user.id = 1

        # Mock the database session
        mock_db = MagicMock()

        # Call the function
        result = await upload_file(file=mock_file, current_user=mock_user, db=mock_db)

        # Verify the result is a Document object
        assert isinstance(result, models.Document)

        # Verify the mocks were called correctly
        mock_makedirs.assert_called_once_with("uploads", exist_ok=True)
        # mock_join.assert_called_once_with("uploads", "test_uuid_test.txt")
        mock_file.read.assert_awaited_once()
        mock_open.assert_called_once_with("uploads/test_uuid_test.txt", "wb")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.anyio
    async def test_upload_unsupported_file_type(self):
        """Test uploading an unsupported file type"""
        # Create a mock file with unsupported extension
        mock_file = MagicMock()
        mock_file.filename = "test.exe"

        # Create a mock user
        mock_user = MagicMock()

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            await upload_file(file=mock_file, current_user=mock_user, db=mock_db)

        # Verify the exception
        assert excinfo.value.status_code == 400
        assert "Unsupported file type" in excinfo.value.detail

    @pytest.mark.anyio
    async def test_upload_file_too_large(self):
        """Test uploading a file that's too large"""
        # Create a mock file
        mock_file = MagicMock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"

        # Make the mock awaitable and return a large file
        mock_file.read = AsyncMock(return_value=b"x" * (11 * 1024 * 1024))

        # Create a mock user
        mock_user = MagicMock()

        # Mock the database session
        mock_db = MagicMock()

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            await upload_file(file=mock_file, current_user=mock_user, db=mock_db)

        # Verify the exception
        assert excinfo.value.status_code == 400
        assert "File too large" in excinfo.value.detail


class TestAskQuestion:
    @pytest.mark.anyio
    async def test_ask_question_success(self):
        """Test asking a question successfully"""
        # Create a mock document
        mock_doc = MagicMock()
        mock_doc.id = 1
        mock_doc.user_id = 1
        mock_doc.extracted_text = "This is a test document"

        # Create a mock user
        mock_user = MagicMock()
        mock_user.id = 1

        # Create a mock request
        mock_request = schemas.AskRequest(document_id=1, question="What is this?")

        # Mock the database session and query
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc

        # Call the function
        result = await ask_question(ask_request=mock_request, current_user=mock_user, db=mock_db)

        # Verify the result
        assert "answer" in result
        assert mock_request.question in result["answer"]

        # Verify the mocks were called correctly
        mock_db.query.assert_called_once_with(models.Document)
        mock_db.query.return_value.filter_by.assert_called_once_with(id=1, user_id=1)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.anyio
    async def test_ask_question_document_not_found(self):
        """Test asking a question for a non-existent document"""
        # Create a mock user
        mock_user = MagicMock()
        mock_user.id = 1

        # Create a mock request
        mock_request = schemas.AskRequest(document_id=999, question="What is this?")

        # Mock the database session and query to return None (document not found)
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        # Call the function and expect an exception
        with pytest.raises(HTTPException) as excinfo:
            await ask_question(ask_request=mock_request, current_user=mock_user, db=mock_db)

        # Verify the exception
        assert excinfo.value.status_code == 404
        assert "Document not found" in excinfo.value.detail

        # Verify the mocks were called correctly
        mock_db.query.assert_called_once_with(models.Document)
        mock_db.query.return_value.filter_by.assert_called_once_with(id=999, user_id=1)


class TestGetHistory:
    def test_get_history_success(self):
        """Test getting history successfully"""
        # Create mock history records
        mock_records = [MagicMock(), MagicMock()]

        # Create a mock user
        mock_user = MagicMock()
        mock_user.id = 1

        # Mock the database session and query
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_records

        # Call the function
        result = get_history(current_user=mock_user, db=mock_db)

        # Verify the result
        assert result == mock_records

        # Verify the mocks were called correctly
        mock_db.query.assert_called_once_with(models.QAHistory)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.order_by.assert_called_once()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.assert_called_once()
