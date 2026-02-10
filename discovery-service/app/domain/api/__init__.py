from .health_check.view import router as health_check_router
from .service.view import router as service_discovery_router

routers = (
    health_check_router,
    service_discovery_router,
)
