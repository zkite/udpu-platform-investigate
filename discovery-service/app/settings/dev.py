import logging

from settings.base import BaseAppSettings


class DevAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Dev Service Discovery"

    logging_level: int = logging.DEBUG


