from typing import List, Optional

from redis.exceptions import RedisError, ResponseError, ReadOnlyError
from redis.asyncio.client import Redis
from services.logging.logger import log as logger

from domain.api.logs.constants import JOB_LOG_PREFIX
from domain.api.logs.schemas import JobLogSchema
from services.redis.exceptions import RedisResponseError


class JobLogService:
    """
    Service for managing job logs in Redis.
    """

    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_all(self) -> List[JobLogSchema]:
        """
        Retrieve all job logs.
        """
        pattern = f"{JOB_LOG_PREFIX}:*"
        try:
            keys = await self._redis.keys(pattern)
            results: List[JobLogSchema] = []
            for key in keys:
                data = await self._redis.hgetall(key)
                results.append(JobLogSchema(**data))
            return results
        except RedisError as e:
            logger.error(f"Redis error in get_all: {e}", exc_info=True)
            raise RedisResponseError(str(e))

    async def create(self, job_log: JobLogSchema) -> JobLogSchema:
        """
        Create a new job log entry.
        """
        key = job_log.key
        try:
            await self._redis.hset(key, mapping=job_log.dict())
        except (ResponseError, ReadOnlyError) as e:
            logger.error(f"Redis error in create for key {key}: {e}", exc_info=True)
            raise RedisResponseError(str(e))
        # return fresh object from store
        return await self.get_by_key(key)

    async def get_by_key(self, key: str) -> JobLogSchema:
        """
        Retrieve a single job log by its full Redis key.
        """
        try:
            data = await self._redis.hgetall(key)
            return JobLogSchema(**data)
        except ResponseError as e:
            logger.error(f"Redis error in get_by_key for key {key}: {e}", exc_info=True)
            raise RedisResponseError(str(e))

    async def get_by_name(self, name: str) -> List[JobLogSchema]:
        """
        Retrieve all job logs with the given job name.
        """
        try:
            all_logs = await self.get_all()
        except RedisResponseError:
            raise
        return [log for log in all_logs if log.name == name]
