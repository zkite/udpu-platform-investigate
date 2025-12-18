from fastapi import Depends
from redis.asyncio.client import Redis
from fastapi import Request

from domain.api.logs.core import JobLogService


def get_redis(request: Request) -> Redis:
    """
    Retrieve Redis connection from FastAPI application state.

    :param request: FastAPI request object.
    :return: Redis connection instance.
    """
    return request.app.state.redis


def get_job_log_service(
    redis: Redis = Depends(get_redis),
) -> JobLogService:
    """
    Dependency that provides JobLogService.
    """
    return JobLogService(redis)
