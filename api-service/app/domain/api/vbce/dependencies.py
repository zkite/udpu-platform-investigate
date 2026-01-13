import logging
from services.logging.logger import log as logger
from statistics import mean

from redis.asyncio.client import Redis
from redis.exceptions import ReadOnlyError, ResponseError

from services.redis.exceptions import RedisResponseError

from .constants import VBCE_ENTITY, VBCE_LOCATION_LIST
from .schemas import Vbce


async def update_vbce_location_list(redis: Redis, location_id: str):
    try:
        await redis.sadd(VBCE_LOCATION_LIST, location_id)
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_vbce_location_list(redis: Redis):
    try:
        return await redis.smembers(VBCE_LOCATION_LIST)
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_vbce(redis: Redis, key: str):
    try:
        return await redis.hgetall(key)
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_vbce_list(redis: Redis):
    vbces = []
    try:
        vbce_keys = [vbce for vbce in await redis.keys(f"{VBCE_ENTITY}:*")
                     if "vbce_locations_list" not in vbce]
        for vbce in vbce_keys:
            vbces.append(await redis.hgetall(vbce))
        return vbces
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_vbce_by_location_id(redis: Redis, location_id: str):
    vbce_list = [vbce for vbce in await redis.keys(f"{VBCE_ENTITY}:*")
                 if "vbce_locations_list" not in vbce]
    for vbce in vbce_list:
        vbce = await redis.hgetall(vbce)
        if vbce["location_id"] == location_id:
            return vbce


async def find_empty_vbce(redis: Redis):
    vbce_list = [vbce for vbce in await redis.keys(f"{VBCE_ENTITY}:*")
                 if "vbce_locations_list" not in vbce]
    for vbce in vbce_list:
        vbce = await redis.hgetall(vbce)
        if int(vbce["current_users"]) == 0 and not vbce["location_id"]:
            return vbce


async def create_vbce(redis: Redis, vbce: Vbce):
    try:
        value = vbce.dict()
        value["available_users"] = value["max_users"]
        await redis.hset(vbce.key, mapping=value)
        await redis.set(vbce.location_id, vbce.name)
        await update_vbce_location_list(redis, vbce.location_id)
        return value
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))

async def delete_vbce(redis: Redis, key: str):
    try:
        await redis.delete(key)
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def patch_vbce(redis: Redis, vbce: dict, vbce_to_update: dict):
    vbce_key = vbce_to_update.pop("key")
    if "location_id" in vbce_to_update and vbce_to_update["location_id"] != vbce["location_id"]:
        await redis.set(vbce_to_update["location_id"], vbce["name"])
        await redis.delete(vbce["location_id"])
        await update_vbce_location_list(redis, vbce_to_update["location_id"])
        await redis.srem(VBCE_LOCATION_LIST, vbce["location_id"])

    for key, value in vbce_to_update.items():
        if value is not None:
            vbce[key] = value

    vbce["available_users"] = int(vbce["max_users"]) - int(vbce["current_users"])
    try:
        await redis.hset(vbce_key, mapping=vbce)
        return vbce
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def update_vbce(redis: Redis, location_id: str, seed_idx: int):
    """
    This function is called after assigning vb user to vbce.
    current_users count and used seed_idx should be updated
    """
    vbce = await get_vbce_by_location_id(redis, location_id)
    if not vbce:
        empty_vbce = await find_empty_vbce(redis)
        if empty_vbce:
            vbce_to_update = Vbce(**empty_vbce)
            vbce_to_update.location_id = location_id
            vbce_to_update.current_users = int(vbce_to_update.current_users) + 1
            vbce_to_update.available_users = int(vbce_to_update.max_users) - int(vbce_to_update.current_users)
            if int(vbce_to_update.current_users) == 1:
                vbce_to_update.seed_idx_used = seed_idx
            else:
                vbce_to_update.seed_idx_used = f"{vbce_to_update.seed_idx_used},{seed_idx}"
            await redis.hset(vbce_to_update.key, mapping=vbce_to_update.dict())
            await redis.set(vbce_to_update.location_id, vbce_to_update.name)
            await update_vbce_location_list(redis, vbce_to_update.location_id)
            return vbce_to_update

        else:
            raise Exception("No empty vbce found")
    else:
        vbce_key = f"{VBCE_ENTITY}:{vbce['name']}"

    vbce["current_users"] = int(vbce["current_users"]) + 1
    vbce["available_users"] = int(vbce["max_users"]) - int(vbce["current_users"])
    if vbce["current_users"] == 1:
        vbce["seed_idx_used"] = seed_idx
    else:
        vbce["seed_idx_used"] = f"{vbce['seed_idx_used']},{seed_idx}"
    await redis.hset(vbce_key, mapping=vbce)
    return vbce


async def calculate_vbce_rates(redis):
    from domain.api.vbuser.dependencies import get_vbusers_by_location
    logger.info("Calculating vbce rates")
    vbce_list = await get_vbce_list(redis)
    try:
        for vbce in vbce_list:
            if int(vbce["current_users"]) > 0:
                vbusers = await get_vbusers_by_location(redis, vbce["location_id"])
                vbusers_current_rates = [int(vbuser["lq_current_rate"]) for vbuser in vbusers]
                vbce["lq_min_rate"] = min(vbusers_current_rates)
                vbce["lq_max_rate"] = max(vbusers_current_rates)
                vbce["lq_mean_rate"] = round(mean(vbusers_current_rates))
                await redis.hset(f"{VBCE_ENTITY}:{vbce['name']}", mapping=vbce)
    except Exception as e:
        logger.error(str(e))
