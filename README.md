# Smart Document Assistant

This repository provides a minimal backend that lets users upload documents and ask questions about them. The service is built with **FastAPI** and uses **SQLite** for storage. Authentication relies on OAuth2 with JWT tokens.

## Technology Stack

- Python 3.10
- FastAPI with Uvicorn
- SQLAlchemy ORM
- Redis (via Docker Compose)
- SQLite for local development
- Docker and Docker Compose
- Dependency installation using [uv](https://github.com/astral-sh/uv)

## Setup

### Environment Variables

The application requires a Google Generative AI API key to function properly. You need to provide this key as an environment variable:

- `GENAI_API_KEY`: Your Google Generative AI API key

When running with Docker Compose, the environment variable is automatically passed from your host system to the container. Inside the container, the application reads this environment variable to authenticate with the Google Generative AI API.

### Running with Docker Compose

Build and run the containers:

```bash
# Set your Google Generative AI API key
export GENAI_API_KEY=your_api_key_here

# Start the services
docker-compose up --build
```

Alternatively, you can create a `.env` file in the project root with your API key. A template file `.env.example` is provided for convenience:

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file with your API key
# Replace 'your_api_key_here' with your actual API key
```

And then run:

```bash
docker-compose up --build
```

This installs all Python dependencies using `uv` and launches the API and Redis containers. The API is available at `http://localhost:8000`.

## API Documentation

The API documentation is automatically generated and can be accessed at:

- **Swagger UI**: `http://localhost:8000/docs` - Interactive documentation with the ability to try out the endpoints
- **ReDoc**: `http://localhost:8000/redoc` - Alternative documentation view

### Creating a user and obtaining a token

1. Register a new user:

```bash
curl -X POST http://localhost:8000/signup -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "pass"}'
```

2. Request an access token:

```bash
curl -X POST http://localhost:8000/token -F "username=test@example.com" -F "password=pass"
```

Use the returned token to authenticate to protected endpoints.

### Upload a document

```bash
curl -X POST http://localhost:8000/upload \
     -H "Authorization: Bearer <TOKEN>" \
     -F "file=@mydoc.pdf"
```

### Ask a question

```bash
curl -X POST http://localhost:8000/ask \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"document_id": 1, "question": "What is this document about?"}'
```

### View history

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/history
```

To stop the services, press `Ctrl+C` or run:

```bash
docker-compose down
```

## Project Layout

```
/app
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── app/
    ├── main.py       # FastAPI entry point with API routes
    ├── models.py     # SQLAlchemy models
    ├── crud.py       # Basic CRUD helpers
    ├── schemas.py    # Pydantic models
    └── dependencies.py
```
