from fastapi import Request
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from config import get_app_settings
from domain.api.service.dependencies import create, get_all
from domain.api.service.schemas import ServiceDiscoverySchema

router = InferringRouter()


@cbv(router)
class ServiceDiscovery:

    settings = get_app_settings()

    @router.get("/services")
    async def get(self, request: Request, service_type: str):
        redis = request.app.state.redis
        return await get_all(redis, service_type)

    @router.post("/services")
    async def post(self, service: ServiceDiscoverySchema, request: Request):
        redis = request.app.state.redis
        return await create(redis, service)
