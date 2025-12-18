from fastapi import FastAPI, Request
from services.logging.logger import log as logger
from redis.asyncio.client import Redis
from redis.exceptions import ConnectionError

from settings.base import BaseAppSettings


async def connect_to_redis(app: FastAPI, settings: BaseAppSettings) -> None:
    logger.info("Connecting to Redis")
    app.state.redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=200,
        socket_connect_timeout=5,
        socket_timeout=10
    )
    try:
        await app.state.redis.ping()
    except ConnectionError:
        logger.info("Can't connect to Redis")
    else:
        logger.info("Connection established")


async def close_redis_connection(app: FastAPI) -> None:
    logger.info("Closing connection to database")
    await app.state.redis.close()
    logger.info("Connection closed")


def get_redis(request: Request) -> Redis:
    """
    Retrieve Redis connection from FastAPI application state.

    :param request: FastAPI request object.
    :return: Redis connection instance.
    """
    return request.app.state.redis