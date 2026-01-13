from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from config import get_app_settings
from services.redis.exceptions import RedisResponseError

from .dependencies import create_vbce, delete_vbce, get_vbce, patch_vbce, get_vbce_list, get_vbce_by_location_id, get_vbce_location_list
from .schemas import Vbce, VbceUpdate
from .constants import VBCE_ENTITY


router = InferringRouter()


@cbv(router)
class VbceResource:
    settings = get_app_settings()

    @router.post("/vbce")
    async def post(self, vbce: Vbce, request: Request):
        redis = request.app.state.redis

        if await get_vbce(redis, vbce.name):
            return JSONResponse(
                status_code=400,
                content={"message": f"Vbce object with name {vbce.name} already exists"},
            )

        # get vbce by location id
        if vbce.location_id:
            vbce_by_location_id = await get_vbce_by_location_id(redis, vbce.location_id)
            if vbce_by_location_id:
                return JSONResponse(
                    status_code=400,
                    content={"message": f"Vbce object with location id {vbce.location_id} already exists"},
                )
        try:
            return await create_vbce(redis, vbce)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.get("/vbce/{vbce_name}")
    async def get(self, vbce_name: str, request: Request):
        redis = request.app.state.redis
        try:
            vbce = await get_vbce(redis, vbce_name)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content=e.message)

        if not vbce:
            return JSONResponse(status_code=404, content={"message": f"Vbce object with name {vbce_name} is not found"})
        return vbce

    @router.patch("/vbce/{vbce_name}", response_model=Vbce)
    async def patch(self, vbce_name: str, vbce_to_update: VbceUpdate, request: Request):
        redis = request.app.state.redis

        vbce_to_update = vbce_to_update.dict(exclude_unset=True)

        try:
            vbce = await get_vbce(redis, vbce_name)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content=e.message)
        if not vbce:
            return JSONResponse(status_code=404, content={"message": f"Vbce object with name {vbce_name} is not found"})

        vbce_to_update["key"] = f"{VBCE_ENTITY}:{vbce['name']}"

        if int(vbce["current_users"]) > 0 and "location_id" in vbce_to_update:
            return JSONResponse(status_code=400, content={"message": "Location id cannot be changed if the VBCE is not empty."})

        if vbce_to_update.get("max_users") and vbce_to_update["max_users"] < 0:
            return JSONResponse(status_code=400, content={"message": "The allowed number of users cannot be less than zero."})

        if vbce_to_update.get("max_users") and vbce_to_update["max_users"] < int(vbce["current_users"]):
            return JSONResponse(status_code=400, content={"message": "The allowed number of users cannot be less than the current number of users."})

        try:
            return await patch_vbce(redis, vbce, vbce_to_update)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content=e.message)

    @router.delete("/vbce/{vbce_name}")
    async def delete(self, vbce_name: str, request: Request):
        redis = request.app.state.redis
        try:
            vbce = await get_vbce(redis, vbce_name)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content=e.message)

        if not vbce:
            return JSONResponse(status_code=404, content={"message": f"Vbce object with name {vbce_name} is not found"})

        try:
            await delete_vbce(redis, vbce_name)
            return JSONResponse(status_code=200, content={"message": f"Vbce object with name {vbce_name} deleted"})
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content=e.message)


@cbv(router)
class VbceListResource:
    settings = get_app_settings()

    @router.get("/vbces")
    async def get(self, request: Request):
        redis = request.app.state.redis
        return await get_vbce_list(redis)

    @router.get("/vbce/locations")
    async def get_locations(self, request: Request):
        redis = request.app.state.redis
        locations = await get_vbce_location_list(redis)
        return list(locations)
