import os
from functools import lru_cache
from typing import Dict, Type

from settings.base import BaseAppSettings
from settings.local import LocalAppSettings
from settings.dev import DevAppSettings
from settings.stage import StageAppSettings

environments: Dict[str, Type[BaseAppSettings]] = {
    "local": LocalAppSettings,
    "dev": DevAppSettings,
    "stage": StageAppSettings,
}


@lru_cache
def get_app_settings() -> BaseAppSettings:
    app_env = os.getenv("UDPU_ENVIRONMENT", "local")
    config = environments[app_env]
    return config()
