# API Versioning Guide

## Overview

This document describes the API versioning strategy for the Smart Document Assistant API. API versioning is implemented to ensure backward compatibility as the API evolves, allowing clients to continue using older versions of the API while new features are added.

## Versioning Strategy

The API uses URI path versioning, where the version is included in the URL path. This approach makes the versioning explicit and easy to understand for API consumers.

### Version Format

All API endpoints are prefixed with the API version in the format `/api/vX`, where `X` is the major version number.

Examples:
- `/api/v1/upload` - Version 1 of the upload endpoint
- `/api/v2/upload` - Version 2 of the upload endpoint (future)

## Current Versions

### v1 (Current)

The first version of the API, available at `/api/v1/`. This version includes the following endpoints:

- Authentication
  - `/api/v1/signup` - Register a new user
  - `/api/v1/token` - Obtain an authentication token

- Documents
  - `/api/v1/upload` - Upload a document
  - `/api/v1/ask` - Ask a question about a document
  - `/api/v1/history` - View question-answer history

- System
  - `/api/v1/health` - Check API health

## Non-versioned Endpoints

Some endpoints are available without a version prefix:

- `/health` - System health check
- `/docs` - API documentation (Swagger UI)
- `/redoc` - API documentation (ReDoc)
- `/` - Redirects to API documentation

## Guidelines for Future Versions

When creating a new API version:

1. **Create a new router**: Create a new router for the new version (e.g., `v2_router = APIRouter(prefix="/api/v2")`)

2. **Copy and modify endpoints**: Copy the endpoints from the previous version and modify them as needed

3. **Maintain backward compatibility**: Ensure that the previous version continues to work as expected

4. **Update documentation**: Update the API documentation to reflect the new version

5. **Communicate changes**: Clearly communicate the changes to API consumers

## Deprecation Policy

When an API version is deprecated:

1. It will continue to be available for at least 6 months after deprecation
2. Deprecation notices will be added to the API documentation
3. Responses will include a deprecation warning header

## Example: Adding a New Version

```python
# Create a new router for v2
v2_router = APIRouter(prefix="/api/v2")

# Define v2 endpoints
@v2_router.post("/upload", response_model=schemas.UploadResponseV2)
async def upload_file_v2(...):
    # New implementation
    ...

# Include the v2 router in the main app
app.include_router(v2_router)
```