import logging

from settings.base import BaseAppSettings


class StageAppSettings(BaseAppSettings):
    debug: bool = True

    title: str = "Stage uDPU API Service"

    logging_level: int = logging.DEBUG
