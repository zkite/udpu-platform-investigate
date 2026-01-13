from services.logging.logger import log as logger

from redis.asyncio.client import Redis
from redis.exceptions import ReadOnlyError, ResponseError

from services.redis.exceptions import RedisResponseError
from domain.api.northbound.dependencies import get_udpu
from domain.api.roles.dependencies import get_udpu_role, get_primary_ghn_interfaces
from domain.api.vbce.dependencies import update_vbce, get_vbce
from domain.api.vbce.constants import VBCE_ENTITY
from utils import get_random_seed_index

from .constants import (SEED_INDEX_HIGH, SEED_INDEX_LOW, VBCE_LOCATION_LIST,
                        VBCE_LOCATION_SEED_IND_LIST, VBUSER_ENTITY)
from .schemas import VBUser


async def location_exist(redis: Redis, location_id: str):
    return await redis.sismember(VBCE_LOCATION_LIST, location_id)


async def get_vbuser(redis: Redis, key: str):
    try:
        return await redis.hgetall(key)
    except ResponseError as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_vbuser_list(redis: Redis):
    vbusers = []
    try:
        users = [user for user in await redis.keys(f"{VBUSER_ENTITY}:*")]
        for user in users:
            vbusers.append(await redis.hgetall(user))
        return vbusers
    except ResponseError as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_vbuser_by_udpu(redis: Redis, udpu: str):
    try:
        vbusers = await redis.keys(f"{VBUSER_ENTITY}:*")
        vbusers = [user for user in vbusers]
        for user in vbusers:
            user = await redis.hgetall(user)
            if user["udpu"] == udpu:
                return user
        return None
    except ResponseError as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def create_vbuser(redis: Redis, vbuser: VBUser):
    try:
        vbuser = vbuser.dict()
        for key, value in vbuser.items():
            if isinstance(value, bool):
                vbuser[key] = int(value)
    except Exception:
        logger.info("Exception for 'vbuser = vbuser.dict()'")

    try:
        if vbuser.get("location_id"):
            logger.info("Create vbuser with location_id")
            return await assign_user_to_vbce(redis, vbuser, vbuser["location_id"])
        else:
            await redis.hset(vbuser.key, mapping=vbuser.serialize())
            logger.info("Create vbuser withOUT location_id")
            return vbuser
    except Exception as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def delete_vbuser(redis: Redis, vbu_uid: str, location_id: str, seed_idx: int):
    try:
        vbce_name = await redis.get(location_id)
        if not vbce_name:
            await redis.delete(f"{VBUSER_ENTITY}:{vbu_uid}")
            return
        vbce_key = f"{VBCE_ENTITY}:{vbce_name}"
        vbce = await get_vbce(redis, vbce_name)
        current_users = int(vbce["current_users"])
        vbce_seeds = vbce.get("seed_idx_used", "")
        vbce_seeds = vbce_seeds.split(",") if vbce_seeds else []
        if str(seed_idx) in vbce_seeds:
            vbce_seeds.remove(str(seed_idx))
        vbce["seed_idx_used"] = ",".join(vbce_seeds)
        if current_users == 1:
            vbce["current_users"] = current_users - 1
            vbce["available_users"] = int(vbce["max_users"]) - int(vbce["current_users"])
            vbce["location_id"] = ""
            await redis.hset(vbce_key, mapping=vbce)
            await redis.srem(VBCE_LOCATION_LIST, location_id)
            await redis.delete(location_id)
        if current_users > 1:
            vbce["current_users"] = current_users - 1
            vbce["available_users"] = int(vbce["max_users"]) - int(vbce["current_users"])
            await redis.hset(vbce_key, mapping=vbce)
        await redis.delete(f"{VBUSER_ENTITY}:{vbu_uid}")
    except (ResponseError, ReadOnlyError) as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def update_vbuser(redis: Redis, vbu_uid: str, vbuser):
    try:
        user = await get_vbuser(redis, vbu_uid)
        user.update(vbuser.dict(exclude_unset=True))
        await redis.hset(f"vbuser_{vbu_uid}", mapping=user)
        return user
    except (ResponseError, ReadOnlyError, Exception) as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def update_vbuser_interfaces(redis: Redis, vbuser: dict, ghn_interface: str, lcmp_interface: str):
    try:
        vbuser["ghn_interface"] = ghn_interface
        vbuser["lcmp_interface"] = lcmp_interface
        await redis.hset(f"{VBUSER_ENTITY}:{vbuser['vb_uid']}", mapping=vbuser)
        return vbuser
    except (ResponseError, ReadOnlyError) as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def assign_user_to_vbce(redis: Redis, vbuser: dict, location_id: str):
    try:
        key = f"{VBUSER_ENTITY}:{vbuser['vb_uid']}"
        vbuser["location_id"] = location_id
        vbuser["seed_idx"] = await get_seed_index(redis, location_id)
        await redis.hset(key, mapping=vbuser)
        await update_vbce(redis, location_id, vbuser["seed_idx"])
        return vbuser
    except (ResponseError, ReadOnlyError) as e:
        logger.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_seed_index(redis: Redis, location_id: str):
    loc_seed_ind_key = f"{VBCE_LOCATION_SEED_IND_LIST}_{location_id}"
    seed_indexes = await redis.hgetall(loc_seed_ind_key)
    return get_random_seed_index(SEED_INDEX_LOW, SEED_INDEX_HIGH, seed_indexes)


async def get_detailed_vbuser(redis: Redis, vbuser: dict):
    # get udpu role by vbuser.udpu
    udpu = await get_udpu(redis, vbuser["udpu"])

    # get role by role name
    role = await get_udpu_role(redis, udpu["role"])

    ghn_interface, lcmp_interface = get_primary_ghn_interfaces(role)
    vbuser["ghn_interface"] = ghn_interface
    vbuser["lcmp_interface"] = lcmp_interface
    return vbuser


async def get_vbusers_by_location(redis: Redis, location: str):
    result = []
    try:
        vbusers = await redis.keys(f"{VBUSER_ENTITY}:*")
        try:
            vbusers = [user for user in vbusers]
        except Exception:
            pass
        for user in vbusers:
            user = await redis.hgetall(user)
            if user["location_id"] == location:
                result.append(user)
    except ResponseError as e:
        logger.error(str(e))
    return result
