import logging

from settings.base import BaseAppSettings


class LocalAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Local Repository Service API"

    logging_level: int = logging.DEBUG

