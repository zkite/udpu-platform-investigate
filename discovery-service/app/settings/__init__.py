from enum import Enum


class AppEnvTypes(Enum):
    base: str = "base"
    prod: str = "prod"
    dev: str = "dev"
    test: str = "test"
