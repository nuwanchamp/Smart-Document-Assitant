# Smart Document Assistant API Documentation

## Overview

The Smart Document Assistant API allows users to upload documents (PDF or TXT), extract text from them, and ask questions about their content. The API includes authentication, document management, and question-answering capabilities.

## Base URL

```
https://api.smartdocumentassistant.com
```

## Authentication

The API uses JWT (JSON Web Token) for authentication. To access protected endpoints, you need to include the token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

### Authentication Endpoints

#### User Registration

```
POST /signup
```

Creates a new user account with the provided email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "strongpassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Status Codes:**
- 200: Success
- 400: Email already registered

#### User Login

```
POST /token
```

Authenticates a user and returns an access token.

**Request Body (Form Data):**
```
username: user@example.com
password: strongpassword123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Status Codes:**
- 200: Success
- 400: Incorrect username or password

## System Endpoints

#### Health Check

```
GET /health
```

Returns a simple status message to confirm the API is running.

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- 200: Success

## Document Management

#### Upload Document

```
POST /upload
```

Uploads a document file (PDF or TXT) and extracts its text content. The file is stored on the server and its text content is extracted for later querying.

**Request:**
- Content-Type: multipart/form-data
- Form field: file (PDF or TXT file)

**Response:**
```json
{
  "id": 1,
  "filename": "sample.pdf",
  "mime_type": "application/pdf",
  "file_size": 125360,
  "uploaded_at": "2023-07-15T14:30:00.000Z"
}
```

**Status Codes:**
- 200: Success
- 400: Unsupported file type (only PDF and TXT are allowed)
- 400: File too large (max 10MB)
- 400: Encrypted PDFs not supported
- 401: Unauthorized

## Question Answering

#### Ask Question

```
POST /ask
```

Asks a question about a previously uploaded document and returns an answer. The question is processed against the document's extracted text content.

**Request Body:**
```json
{
  "document_id": 1,
  "question": "What are the main points in this document?"
}
```

**Response:**
```json
{
  "answer": "The main points in this document are..."
}
```

**Status Codes:**
- 200: Success
- 404: Document not found or doesn't belong to the user
- 401: Unauthorized

## History

#### Get Question-Answer History

```
GET /history
```

Retrieves the history of questions and answers for the authenticated user, ordered by most recent first.

**Response:**
```json
[
  {
    "id": 1,
    "document_id": 1,
    "question": "What are the main points in this document?",
    "answer": "The main points in this document are...",
    "created_at": "2023-07-15T15:30:00.000Z"
  },
  {
    "id": 2,
    "document_id": 1,
    "question": "Who is the author of this document?",
    "answer": "The author of this document is...",
    "created_at": "2023-07-15T15:25:00.000Z"
  }
]
```

**Status Codes:**
- 200: Success
- 401: Unauthorized

## Data Models

### User

Represents a registered user in the system.

**Properties:**
- id: Integer (Primary Key)
- email: String (Unique, Required)
- hashed_password: String (Required)
- created_at: DateTime

### Document

Represents an uploaded document.

**Properties:**
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key to User)
- filename: String (Required)
- mime_type: String (Required)
- file_size: Integer (Required)
- storage_path: String (Required)
- extracted_text: Text (Required)
- uploaded_at: DateTime

### QAHistory

Represents a question-answer interaction.

**Properties:**
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key to User)
- document_id: Integer (Foreign Key to Document)
- question: Text (Required)
- answer: Text (Required)
- tokens_used: Integer
- latency_ms: Integer
- created_at: DateTime

## Error Handling

The API returns standard HTTP status codes to indicate the success or failure of a request. In case of an error, the response body will contain a JSON object with a `detail` field describing the error:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. If you exceed the rate limit, you will receive a 429 Too Many Requests response.

## Notes

- All timestamps are in UTC and follow the ISO 8601 format.
- The maximum file size for uploads is 10MB.
- Only PDF and TXT files are supported for upload.
- Encrypted PDFs are not supported.