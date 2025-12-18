import logging

from settings.base import BaseAppSettings


class DevAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Dev Repository Service API"

    logging_level: int = logging.DEBUG


