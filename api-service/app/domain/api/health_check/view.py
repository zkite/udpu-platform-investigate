from fastapi_utils.cbv import cbv
from fastapi import APIRouter

router = APIRouter()


@cbv(router)
class HealthCheck:
    @router.get("/health")
    def get(self):
        return {"status": "success"}
