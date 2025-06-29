from typing import Generator, Callable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from fastapi import Request, HTTPException
from limits import parse_many
from limits.storage import RedisStorage
from limits.strategies import MovingWindowRateLimiter
import redis

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize Redis client
redis_client = redis.from_url(REDIS_URL)
storage = RedisStorage(REDIS_URL)
limiter = MovingWindowRateLimiter(storage)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def rate_limit(limit_string: str):
    """
    Rate limiting dependency that can be applied to FastAPI endpoints.

    Args:
        limit_string: A string in the format "X/second", "X/minute", "X/hour", "X/day"
                     where X is the number of requests allowed in that time period.

    Example:
        @app.get("/endpoint", dependencies=[Depends(rate_limit("10/minute"))])
        def endpoint():
            return {"message": "Rate limited endpoint"}
    """
    items = parse_many(limit_string)

    def _rate_limit_dependency(request: Request):
        client_ip = request.client.host
        endpoint = request.url.path

        # Create a unique key for this client and endpoint
        key = f"{client_ip}:{endpoint}"

        for item in items:
            if not limiter.hit(item, key):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )

        return True

    return _rate_limit_dependency
