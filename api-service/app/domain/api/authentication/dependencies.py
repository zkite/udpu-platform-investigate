from fastapi import Depends, Request
from redis.asyncio.client import Redis
from domain.api.authentication.core import StampService


def get_redis(request: Request) -> Redis:
    """
    Retrieve Redis connection from FastAPI application state.

    :param request: FastAPI request object.
    :return: Redis connection instance.
    """
    return request.app.state.redis


def get_stamp_service(
    redis: Redis = Depends(get_redis),
) -> StampService:
    """
    Dependency that provides StampService.

    :param redis: Redis client.
    :return: StampService instance.
    """
    return StampService(redis)
