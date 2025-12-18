
import json
import re

from redis.asyncio import Redis
from redis.exceptions import RedisError
from services.logging.logger import log as logger
from services.redis.exceptions import RedisResponseError
from domain.api.exceptions import RecordNotFound
from domain.api.roles.constants import ROLE_PREFIX
from domain.api.roles.schemas import UdpuRole, UdpuRoleClone, UdpuRoleUpdate
from domain.api.northbound.constants import UDPU_ENTITY


def _build_mapping(data: dict) -> dict[str, str]:
    # prepare flat mapping for redis.hset
    return {
        "name": data["name"],
        "description": data["description"],
        "wireguard_tunnel": json.dumps(data["wireguard_tunnel"]),
        "job_control": json.dumps(data["job_control"]),
        "interfaces": json.dumps(data["interfaces"]),
    }


async def create_new_role(redis: Redis, role: UdpuRole) -> dict:
    try:
        payload = role.model_dump()
        mapping = _build_mapping(payload)
        await redis.hset(role.key, mapping=mapping)
        return payload
    except RedisError as e:
        logger.error(e)
        raise RedisResponseError(message=str(e))


async def get_udpu_role(redis: Redis, name: str) -> dict | None:
    key = f"{ROLE_PREFIX}:{name}"
    try:
        data = await redis.hgetall(key)
        if not data:
            return None
        result: dict = {}
        for field, val in data.items():
            if field in ("wireguard_tunnel", "job_control", "interfaces"):
                result[field] = json.loads(val)
            else:
                result[field] = val
        return result
    except RedisError as e:
        logger.error(e)
        raise RedisResponseError(message=str(e))


async def list_udpu_roles(redis: Redis) -> list[dict]:
    try:
        roles: list[dict] = []
        async for key in redis.scan_iter(f"{ROLE_PREFIX}:*"):
            _, name = key.split(":", 1)
            role = await get_udpu_role(redis, name)
            if role:
                roles.append(role)
        return roles
    except RedisError as e:
        logger.error(e)
        raise RedisResponseError(message=str(e))


async def update_role(redis: Redis, name: str, role_update: UdpuRoleUpdate) -> dict:
    old_key = f"{ROLE_PREFIX}:{name}"
    update_data = role_update.model_dump()
    try:
        if not await redis.exists(old_key):
            msg = f"Udpu role with name = {name} not found"
            logger.error(msg)
            raise RecordNotFound(title=name, detail=msg)

        existing = await get_udpu_role(redis, name)
        existing.update(update_data)
        mapping = _build_mapping(existing)

        if name != update_data["name"]:
            await redis.delete(old_key)
            new_key = f"{ROLE_PREFIX}:{update_data['name']}"
            await redis.hset(new_key, mapping=mapping)

            # update related UDPU entities
            pattern = re.compile(r"[a-f0-9]{16}")
            async for udpu_key in redis.scan_iter(f"{UDPU_ENTITY}:*"):
                _, uuid = udpu_key.split(":", 1)
                if pattern.fullmatch(uuid):
                    udpu_data = await redis.hgetall(udpu_key)
                    if udpu_data.get("role") == name:
                        udpu_data["role"] = update_data["name"]
                        await redis.hset(udpu_key, mapping=udpu_data)
        else:
            await redis.hset(old_key, mapping=mapping)

        return existing
    except RedisError as e:
        logger.error(e)
        raise RedisResponseError(message=str(e))


async def clone_role(redis: Redis, role_clone: UdpuRoleClone) -> None:
    key = role_clone.key
    new_key = role_clone.new_role_key
    try:
        data = await redis.hgetall(key)
        if not data:
            return
        mapping = dict(data)
        mapping["name"] = role_clone.new_role_name
        await redis.hset(new_key, mapping=mapping)
    except RedisError as e:
        logger.error(e)
        raise RedisResponseError(message=str(e))


async def delete_role(redis: Redis, name: str) -> None:
    key = f"{ROLE_PREFIX}:{name}"
    try:
        await redis.delete(key)
    except RedisError as e:
        logger.error(e)
        raise RedisResponseError(message=str(e))
