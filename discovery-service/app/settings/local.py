import logging

from settings.base import BaseAppSettings


class LocalAppSettings(BaseAppSettings):

    debug: bool = True

    title: str = "Local Service Discovery"

    logging_level: int = logging.DEBUG
