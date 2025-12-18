import logging

from settings.base import BaseAppSettings


class LocalAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Local uDPU API Service"

    logging_level: int = logging.DEBUG


