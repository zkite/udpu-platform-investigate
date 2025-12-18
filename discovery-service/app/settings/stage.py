import logging

from settings.base import BaseAppSettings


class StageAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Stage Discovery Service"

    logging_level: int = logging.DEBUG
