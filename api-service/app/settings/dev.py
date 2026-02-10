import logging

from settings.base import BaseAppSettings


class DevAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Dev uDPU API Service"

    logging_level: int = logging.DEBUG


