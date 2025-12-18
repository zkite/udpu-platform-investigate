from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

router = InferringRouter()


@cbv(router)
class HealthCheck:
    @router.get("/health")
    def get(self):
        return {"status": "success"}
