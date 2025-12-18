from .authentication.view import router as auth_router
from .health_check.view import router as health_check_router
from .jobs.queues.view import router as queue_router
from .jobs.view import router as job_router
from .logs.view import router as log_router
from .northbound.view import router as northbound_router
from .roles.view import router as roles_router
from .vbce.view import router as vbce_router
from .vbuser.view import router as vbuser_router
from .websocket.constants import WS_PATH
from .websocket.view import ws_router as ws_router
from .wireguard.view import router as wireguard_router

routers = (
    health_check_router,
    northbound_router,
    vbce_router,
    vbuser_router,
    roles_router,
    ws_router,
    job_router,
    queue_router,
    log_router,
    auth_router,
    wireguard_router,
)

ws_urls = (WS_PATH,)
