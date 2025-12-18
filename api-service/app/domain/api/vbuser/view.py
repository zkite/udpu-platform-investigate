from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi import APIRouter

from config import get_app_settings
from services.redis.exceptions import RedisResponseError


from .dependencies import (update_vbuser, get_detailed_vbuser, get_vbuser, get_vbuser_list)

router = APIRouter()


@cbv(router)
class VBUserResource:
    settings = get_app_settings()

    @router.get("/vbuser/{vb_uid}")
    async def get(self, vb_uid: str, request: Request):
        redis = request.app.state.redis

        vbuser = await get_vbuser(redis, vb_uid)
        if not vbuser:
            return JSONResponse(
                status_code=400,
                content={"message": f"VB user object with vb_uid {vb_uid} is not found"},
            )

        return await get_detailed_vbuser(redis, vbuser)

    @router.patch("/vbuser/{vbu_uid}")
    async def patch(self, vbu_uid: str, vbuser, request: Request):
        redis = request.app.state.redis

        if not await get_vbuser(redis, vbu_uid):
            return JSONResponse(
                status_code=404,
                content={"message": f"VB user object with vb_uid {vbu_uid} not found"},
            )

        try:
            return await update_vbuser(redis, vbu_uid, vbuser)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})


@cbv(router)
class VBUserListResource:
    settings = get_app_settings()

    @router.get("/vbusers")
    async def get(self, request: Request):
        redis = request.app.state.redis
        return await get_vbuser_list(redis)
