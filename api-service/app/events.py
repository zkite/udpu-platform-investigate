from typing import Callable

from fastapi import FastAPI
from services.logging.logger import log as logger

from services.discovery.register import register_service
from services.redis import close_redis_connection, connect_to_redis
from services.scheduler import shutdown_scheduler, start_scheduler, vbce_scheduler
from settings.base import BaseAppSettings
from domain.api.vbce.dependencies import calculate_vbce_rates


def create_start_app_handler(app: FastAPI, settings: BaseAppSettings) -> Callable:
    """
    Create a startup event handler for the FastAPI application.

    This handler connects to Redis, starts the scheduler for service registration,
    and schedules VBCE rate calculations.

    :param app: FastAPI application instance.
    :param settings: Application settings instance.
    :return: Asynchronous startup event handler.
    """

    async def start_app() -> None:
        # Connect to Redis and store the connection in app.state
        await connect_to_redis(app, settings)
        # Start scheduler tasks for service registration and VBCE rate calculation
        #vbce_scheduler(app, func=calculate_vbce_rates, args=[app.state.redis])
        start_scheduler(app, func=register_service, args=[settings])

    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:
    """
    Create a shutdown event handler for the FastAPI application.

    This handler closes the Redis connection and shuts down the scheduler.

    :param app: FastAPI application instance.
    :return: Asynchronous shutdown event handler.
    """

    @logger.catch
    async def stop_app() -> None:
        # Close Redis connection
        await close_redis_connection(app)
        # Shutdown scheduler tasks
        shutdown_scheduler(app)

    return stop_app
