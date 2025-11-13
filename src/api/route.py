"""
Main FastAPI application setup with routers.
Configures CORS, middleware, and includes all API routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.routers import documents, categories, inference


# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered document management and summarization platform"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router)
app.include_router(categories.router)
app.include_router(inference.router)


@app.get("/", tags=["health"])
async def root():
    """
    Health check endpoint.
    
    Returns:
        Server status message
    """
    return {
        "message": "Server is running",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Detailed health check endpoint.
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }
