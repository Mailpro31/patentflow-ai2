from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.patents import router as patents_router
from app.routers.projects import router as projects_router

__all__ = [
    "health_router",
    "auth_router",
    "users_router",
    "patents_router",
    "projects_router",
]
