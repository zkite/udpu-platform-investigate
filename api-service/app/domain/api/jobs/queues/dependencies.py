import logging
from uuid import UUID

from redis.exceptions import ReadOnlyError, ResponseError

from services.redis.exceptions import RedisResponseError
from domain.api.jobs.queues.constants import QUEUE_PREFIX


async def check_queue_identifier_type(redis, identifier):
    if await get_queue_by_name(redis, identifier):
        return "name"
    if await get_queue_by_id(redis, identifier):
        return "uid"
    return None


def check_uuid_type(value):
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def check_jobs_identifier_type(jobs):
    if all([check_uuid_type(j) for j in jobs]):
        return "uid"
    if any([check_uuid_type(j) for j in jobs]):
        return "error"
    return "name"


async def get_all_queues(redis):
    queues = []
    queue_keys = await redis.keys(f"{QUEUE_PREFIX}_*")
    for key in queue_keys or []:
        q = await redis.hgetall(key)
        queues.append(q)
    return queues


async def get_queue_by_role(role_name, redis):
    queues = await get_all_queues(redis)
    for q in queues:
        if role_name == q["role"]:
            return q
    return {}


async def get_queue_by_name(redis, name):
    try:
        name = name.decode()
    except Exception:
        pass
    try:
        queues_keys = await redis.keys(f"{QUEUE_PREFIX}_*")
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=e)
    for key in queues_keys:
        job = await get_queue_by_id(redis, key)
        try:
            job = job
        except Exception:
            pass
        if job["name"] == name:
            return job
    return None


async def get_queue_by_id(redis, key):
    try:
        key = key.decode()
    except Exception:
        pass
    if not key.startswith(QUEUE_PREFIX):
        key = f"{QUEUE_PREFIX}_{key}"
    try:
        q = await redis.hgetall(key)
        try:
            q = q
        except Exception:
            pass
        return q
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=e)


async def check_queue_uniqueness(redis, name):
    queue_names = set()
    try:
        queues = await redis.keys(f"{QUEUE_PREFIX}_*")
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))
    for q in queues or []:
        queue_names.add(await redis.hget(q, "name"))
    return not (name in queue_names)


async def create_queue(redis, queue):
    try:
        await redis.hset(queue.key, mapping=queue.serialize())
    except (ResponseError, ReadOnlyError) as e:
        logging.error(e)
        raise RedisResponseError(message=e)
    return await get_queue_by_id(redis, queue.key)


async def is_queue_role_unique(redis, role_name):
    queues = await get_all_queues(redis)
    for q in queues:
        if q["role"] == role_name:
            return False
    return True


async def update_queue(redis, queue):
    try:
        await redis.hset(name=queue.key, mapping=queue.serialize())
    except ResponseError as e:
        logging.error(e)
        raise RedisResponseError(message=e)
    return await get_queue_by_id(redis, queue.key)


async def delete_queue(redis, uid):
    queue_key = f"{QUEUE_PREFIX}_{uid}"
    try:
        await redis.delete(queue_key)
    except ResponseError as e:
        logging.error(e)
        raise RedisResponseError(message=e)
