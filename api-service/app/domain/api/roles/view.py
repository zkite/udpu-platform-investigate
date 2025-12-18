
import logging
from typing import Union
from fastapi import Request, APIRouter
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv

from services.redis.exceptions import RedisResponseError
from domain.api.exceptions import RecordNotFound
from .dependencies import (
    clone_role,
    create_new_role,
    delete_role,
    get_udpu_role,
    list_udpu_roles,
    update_role,
)
from .schemas import UdpuRole, UdpuRoleClone, UdpuRoleUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

@cbv(router)
class RolesView:
    """
    Endpoints for managing UDPU roles.
    """

    @router.post("/roles", response_model=dict, status_code=201)
    async def post(self, role: UdpuRole, request: Request) -> Union[JSONResponse, dict]:
        """
        Create a new UDPU role.

        :param role: The UDPU role data to create.
        :param request: The FastAPI request instance.
        :returns: The created role as a dict.
        """
        redis = request.app.state.redis
        try:
            existing = await get_udpu_role(redis, role.name)
        except RedisResponseError as e:
            logger.error("Error checking existing role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

        if existing:
            return JSONResponse(
                status_code=400,
                content={"message": f"Udpu role with name = {role.name} already exists"},
            )
        try:
            created = await create_new_role(redis, role)
            return created
        except RedisResponseError as e:
            logger.error("Error creating role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.get("/roles/{name}", response_model=dict)
    async def get(self, name: str, request: Request) -> Union[JSONResponse, dict]:
        """
        Retrieve a UDPU role by name.

        :param name: The name of the role.
        :param request: The FastAPI request instance.
        :returns: The role data as dict or 404 if not found.
        """
        redis = request.app.state.redis
        try:
            role = await get_udpu_role(redis, name)
        except RedisResponseError as e:
            logger.error("Error retrieving role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

        if not role:
            logger.warning("Role not found: %s", name)
            return JSONResponse(status_code=404, content={"message": f"Udpu role with name = {name} not found"})
        return role

    @router.get("/roles", response_model=list)
    async def list(self, request: Request) -> Union[JSONResponse, list]:
        """
        List all UDPU roles.

        :param request: The FastAPI request instance.
        :returns: A list of role dicts.
        """
        redis = request.app.state.redis
        try:
            return await list_udpu_roles(redis)
        except RedisResponseError as e:
            logger.error("Error listing roles: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.patch("/roles/{name}", response_model=dict)
    async def patch(self, name: str, role: UdpuRoleUpdate, request: Request) -> Union[JSONResponse, dict]:
        """
        Update an existing UDPU role.

        :param name: The current name of the role.
        :param role: The updated role data.
        :param request: The FastAPI request instance.
        :returns: The updated role as dict.
        """
        redis = request.app.state.redis
        try:
            updated = await update_role(redis, name, role)
            return updated
        except RecordNotFound as e:
            logger.warning("Role update failed, not found: %s", e.detail)
            return JSONResponse(status_code=404, content={"message": e.detail})
        except RedisResponseError as e:
            logger.error("Error updating role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.post("/roles/clone", response_model=dict, status_code=201)
    async def clone(self, role_clone: UdpuRoleClone, request: Request) -> Union[JSONResponse, dict]:
        """
        Clone an existing UDPU role to a new role.

        :param role_clone: The source and new role names.
        :param request: The FastAPI request instance.
        :returns: The cloned role as dict.
        """
        redis = request.app.state.redis
        try:
            source = await get_udpu_role(redis, role_clone.name)
        except RedisResponseError as e:
            logger.error("Error retrieving source role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

        if not source:
            return JSONResponse(status_code=404, content={"message": f"Udpu role with name {role_clone.name} not found"})

        try:
            existing = await get_udpu_role(redis, role_clone.new_role_name)
        except RedisResponseError as e:
            logger.error("Error checking new role existence: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

        if existing:
            return JSONResponse(status_code=400, content={"message": f"Udpu role with name {role_clone.new_role_name} already exists"})

        try:
            await clone_role(redis, role_clone)
            cloned = await get_udpu_role(redis, role_clone.new_role_name)
            return cloned or {}
        except RedisResponseError as e:
            logger.error("Error cloning role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.delete("/roles/{name}", response_model=dict)
    async def delete(self, name: str, request: Request) -> Union[JSONResponse, dict]:
        """
        Delete a UDPU role by name.

        :param name: The name of the role to delete.
        :param request: The FastAPI request instance.
        :returns: A success message dict.
        """
        redis = request.app.state.redis
        try:
            existing = await get_udpu_role(redis, name)
        except RedisResponseError as e:
            logger.error("Error retrieving role for deletion: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})

        if not existing:
            return JSONResponse(status_code=404, content={"message": f"Udpu role with name {name} not found"})

        try:
            await delete_role(redis, name)
            return {"message": f"Udpu role with name {name} deleted"}
        except RedisResponseError as e:
            logger.error("Error deleting role: %s", e.message)
            return JSONResponse(status_code=500, content={"message": e.message})