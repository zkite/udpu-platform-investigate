from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseSettings


class BaseAppSettings(BaseSettings):
    debug: bool = False
    docs_url: str = "/docs"
    openapi_prefix: str = ""
    openapi_url: str = "/openapi.json"
    redoc_url: str = "/redoc"
    title: str = "Service discovery API Service"
    version: str = "0.1.0"

    max_connection_count: int = 10
    min_connection_count: int = 10

    allowed_hosts: List[str] = ["*"]

    loggers: Tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    redis_user: Optional[str] = None
    redis_pass: Optional[str] = None
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None

    # service root dir
    root_dir: str = Path(__file__).parent.parent.__str__()

    @property
    def redis_url(self):
        if self.redis_pass and self.redis_user:
            url = "redis://{username}:{password}@{host}:{port}"
            return url.format(
                username=self.redis_user,
                password=self.redis_pass,
                host=self.redis_host,
                port=self.redis_port,
            )
        return "redis://{host}:{port}".format(host=self.redis_host, port=self.redis_port)

    @property
    def fastapi_kwargs(self) -> Dict[str, Any]:
        return {
            "debug": self.debug,
            "docs_url": self.docs_url,
            "openapi_prefix": self.openapi_prefix,
            "openapi_url": self.openapi_url,
            "redoc_url": self.redoc_url,
            "title": self.title,
            "version": self.version,
        }

    class Config:
        validate_assignment = True

