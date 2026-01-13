
import json
import re

from redis.asyncio import Redis
from redis.exceptions import RedisError
from services.logging.logger import log as logger
from services.redis.exceptions import RedisResponseError
from domain.api.exceptions import RecordNotFound
from domain.api.roles.constants import ROLE_PREFIX
from domain.api.roles.schemas import UdpuRole, UdpuRoleClone, UdpuRoleUpdate
from domain.api.jobs.constants import JOB_PREFIX
from domain.api.jobs.queues.constants import QUEUE_PREFIX
from domain.api.northbound.constants import UDPU_ENTITY


def _normalize_interfaces(interfaces: dict) -> dict:
    if not interfaces:
        return {"management_vlan": {}, "ghn_ports": []}

    normalized = dict(interfaces)
    ghn_ports = normalized.get("ghn_ports")
    if isinstance(ghn_ports, dict):
        ports_list = []
        if "port_1" in ghn_ports:
            ports_list.append(ghn_ports.get("port_1") or {})
            if "port_2" in ghn_ports:
                ports_list.append(ghn_ports.get("port_2") or {})
        else:
            ports_list.extend(ghn_ports.values())
        normalized["ghn_ports"] = ports_list
    elif isinstance(ghn_ports, list):
        normalized["ghn_ports"] = ghn_ports
    else:
        normalized["ghn_ports"] = []
    return normalized


def get_primary_ghn_interfaces(role: dict) -> tuple[str, str]:
    interfaces = _normalize_interfaces((role or {}).get("interfaces") or {})
    ports = interfaces.get("ghn_ports") or []
    if not ports:
        return "", ""
    port = ports[0] or {}
    return port.get("ghn_interface", ""), port.get("lcmp_interface", "")


async def _update_role_in_jobs(redis: Redis, old_name: str, new_name: str) -> None:
    async for key in redis.scan_iter(f"{JOB_PREFIX}:*"):
        data = await redis.hgetall(key)
        if data and data.get("role") == old_name:
            await redis.hset(key, mapping={"role": new_name})


async def _update_role_in_queues(redis: Redis, old_name: str, new_name: str) -> None:
    async for key in redis.scan_iter(f"{QUEUE_PREFIX}:*"):
        data = await redis.hgetall(key)
        if data and data.get("role") == old_name:
            await redis.hset(key, mapping={"role": new_name})


def _build_mapping(data: dict) -> dict[str, str]:
    # prepare flat mapping for redis.hset
    interfaces = _normalize_interfaces(data["interfaces"])
    return {
        "name": data["name"],
        "description": data["description"],
        "wireguard_tunnel": json.dumps(data["wireguard_tunnel"]),
        "job_control": json.dumps(data["job_control"]),
        "interfaces": json.dumps(interfaces),
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
        if "interfaces" in result:
            result["interfaces"] = _normalize_interfaces(result.get("interfaces") or {})
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

            # update related entities
            pattern = re.compile(r"[a-f0-9]{16}")
            async for udpu_key in redis.scan_iter(f"{UDPU_ENTITY}:*"):
                _, uuid = udpu_key.split(":", 1)
                if pattern.fullmatch(uuid):
                    udpu_data = await redis.hgetall(udpu_key)
                    if udpu_data.get("role") == name:
                        udpu_data["role"] = update_data["name"]
                        await redis.hset(udpu_key, mapping=udpu_data)
            await _update_role_in_jobs(redis, name, update_data["name"])
            await _update_role_in_queues(redis, name, update_data["name"])
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
