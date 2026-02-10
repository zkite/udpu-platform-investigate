import logging

from fastapi.security import HTTPBasic
from redis.asyncio.client import Redis
from redis.exceptions import ReadOnlyError, ResponseError

from services.exceptions import RedisResponseError
from services.utils import decode_dict, redis_key_prefix

from .constants import REPO_ENTITY
from .schemas import Repository

security = HTTPBasic()


@redis_key_prefix(REPO_ENTITY)
async def get_repository(redis: Redis, key: str):
    try:
        repo = await redis.hgetall(key)
        return decode_dict(repo)
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def create_repository(redis: Redis, repo: Repository):
    try:
        await redis.hset(repo.repository_key, mapping=repo.serialize())
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def patch_repository(redis: Redis, stored_repo, updated_data):
    repo = Repository(**stored_repo)
    updated_repo = repo.copy(update=updated_data)

    await create_repository(redis, updated_repo)

    return updated_repo


@redis_key_prefix(REPO_ENTITY)
async def increment_number_of_downloads(redis: Redis, key: str):
    try:
        await redis.hincrby(key, "number_of_downloads", 1)
    except ResponseError as e:
        logging.error(str(e))
