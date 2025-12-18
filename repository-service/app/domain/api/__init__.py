from .health_check.view import router as health_check_router
from .repository.view import router as repository_router

routers = (
    health_check_router,
    repository_router,
)
