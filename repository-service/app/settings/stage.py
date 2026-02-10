import logging

from settings.base import BaseAppSettings


class StageAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Stage Repository Service API"

    logging_level: int = logging.DEBUG


