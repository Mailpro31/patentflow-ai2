from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.middleware import (
    configure_security_middleware,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler
)
from app.routers import (
    health_router,
    auth_router,
    users_router,
    patents_router,
    projects_router,
)
from app.routers.ai_generation import router as ai_router
from app.routers.diagram_generation import router as diagram_router
from app.routers.payment_routes import router as payment_router
from app.routers.blockchain_routes import router as blockchain_router
from app.routers.annuity_routes import router as annuity_router



# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    try:
        # Initialize database and enable pgvector
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# API Tags Metadata
tags_metadata = [
    {
        "name": "Authentication",
        "description": "Operations for user authentication and authorization (OAuth2, Magic Links, JWT).",
    },
    {
        "name": "Users",
        "description": "Manage user profiles and settings.",
    },
    {
        "name": "Projects",
        "description": "Create and manage patent projects.",
    },
    {
        "name": "AI Generation",
        "description": "AI-powered patent drafting and analysis.",
    },
    {
        "name": "Payments",
        "description": "Stripe payment integration and subscription management.",
    },
]

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    # PatentFlow AI API
    
    Backend API for the PatentFlow AI platform, facilitating automated patent drafting, analysis, and management.
    
    ## Key Features
    * **AI Generation**: Generate patent drafts, claims, and technical descriptions using LLMs.
    * **Authentication**: Google OAuth2 and Magic Link authentication.
    * **Payments**: Stripe integration for subscription and one-time payments.
    * **Blockchain**: Timestamping and proof of anteriority using Woleet.
    * **Search**: Vector-based semantic search for prior art.
    """,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    debug=settings.DEBUG,
    contact={
        "name": "PatentFlow AI Support",
        "url": "https://patentflow.ai/support",
        "email": "support@patentflow.ai",
    },
)


# Configure middleware
configure_security_middleware(app)


# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


# Register routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(patents_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(ai_router)  # AI generation endpoints
app.include_router(diagram_router)  # Diagram generation endpoints
app.include_router(payment_router)  # Stripe payments
app.include_router(blockchain_router)  # Blockchain proof of anteriority
app.include_router(annuity_router)  # INPI annuities


@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
