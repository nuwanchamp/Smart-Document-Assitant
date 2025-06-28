# Smart Document Assistant

This repository contains the starting point of a document question answering service. It currently exposes a `/health` endpoint and runs inside Docker.

## Technology Stack

- Python 3.10
- FastAPI with Uvicorn
- Redis (via Docker Compose)
- SQLite for local development
- Docker and Docker Compose
- Dependency installation using [uv](https://github.com/astral-sh/uv)

## Setup

Build and run the containers:

```bash
docker-compose up --build
```

This builds the image, installs requirements with `uv`, and starts both the API and Redis containers.

Visit `http://localhost:8000/health` to verify the application is running.

To stop the services, hit `Ctrl+C` or run:

```bash
docker-compose down
```

## Project Layout

```
/app
├── Dockerfile          # Image used by docker-compose
├── docker-compose.yml  # Local orchestration
├── requirements.txt    # Python dependencies
└── app/
    └── main.py         # FastAPI entry point
```

More components will be added as development continues.
