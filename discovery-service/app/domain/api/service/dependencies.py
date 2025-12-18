import logging

from redis.asyncio.client import Redis
from redis.exceptions import ReadOnlyError, ResponseError

from domain.api.service.constants import SERVICE_DISCOVERY_PREFIX
from domain.api.service.schemas import ServiceDiscoverySchema


class RedisResponseError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


async def get(redis: Redis, key: str):
    if not key.startswith(SERVICE_DISCOVERY_PREFIX):
        key = f"{SERVICE_DISCOVERY_PREFIX}_{key}"
    try:
        return await redis.hgetall(key)
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=e)


async def create(redis: Redis, obj: ServiceDiscoverySchema):
    try:
        await redis.hset(obj.key, mapping=obj.serialize())
    except (ResponseError, ReadOnlyError) as e:
        logging.error(e)
        raise RedisResponseError(message=e)
    return await get(redis, obj.key)


async def get_all(redis: Redis, service_type: str):
    objects = []
    objects_keys = await redis.keys(f"{SERVICE_DISCOVERY_PREFIX}_{service_type}_*")
    for key in objects_keys or []:
        objects.append(await redis.hgetall(key))
    return objects
