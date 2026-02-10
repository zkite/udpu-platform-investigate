from typing import Callable

from fastapi import FastAPI
from services.logging.logger import log as logger

from services.redis import close_redis_connection, connect_to_redis
from settings.base import BaseAppSettings


def create_start_app_handler(app: FastAPI, settings: BaseAppSettings) -> Callable:  # type: ignore
    async def start_app() -> None:
        await connect_to_redis(app, settings)

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:  # type: ignore
    @logger.catch
    async def stop_app() -> None:
        await close_redis_connection(app)

    return stop_app
