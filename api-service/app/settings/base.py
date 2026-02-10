from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Application settings for the uDPU platform."""

    # ------------------------------------------------------------------
    # FastAPI metadata
    # ------------------------------------------------------------------
    debug: bool = False
    docs_url: str = "/docs"
    openapi_prefix: str = ""
    openapi_url: str = "/openapi.json"
    redoc_url: str = "/redoc"
    title: str = "uDPU API Service"
    version: str = "0.1.0"

    # ------------------------------------------------------------------
    # Discovery‑service
    # ------------------------------------------------------------------
    discovery_service_host: str = "localhost"
    discovery_service_port: int = 8886

    # ------------------------------------------------------------------
    # HTTP server
    # ------------------------------------------------------------------
    server_host: str = "161.184.221.236"
    server_port: int = 8888

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    redis_user: Optional[str] = None
    redis_pass: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379

    # ------------------------------------------------------------------
    # File‑system
    # ------------------------------------------------------------------
    root_dir: Path = Path(__file__).resolve().parent.parent

    # ------------------------------------------------------------------
    # WireGuard defaults (model *fields* — may be overridden via env)
    # ------------------------------------------------------------------
    WG_VPN_CIDR: str = "10.66.0.0/16"
    DEFAULT_POOL: str = "10.66.0.0/24,10.66.1.0/24,10.66.2.0/24"
    WG_SERVER_IP: str = "10.66.0.1/16"
    WG_SERVER_PORT: int = 51820

    FREE_CLIENT_IPS_KEY: str = "udpu:wg:free:client:ips"
    ALLOCATED_CLIENT_IPS_KEY: str = "udpu:wg:allocated:client:ips"

    WG_MAX_RETRIES: int = 5
    WG_BACKOFF_FACTOR: float = 0.2

    WG_ROUTES: str = "10.250.0.0/16,10.251.0.0/16"

    # ------------------------------------------------------------------
    # WireGuard *constants* (not model fields)
    # ------------------------------------------------------------------
    WG_CONFIG_DIR: ClassVar[str] = "/etc/wireguard"
    WG_INTERFACE: ClassVar[str] = "wg0"

    # This path can be overridden via env‑var; therefore it is a *field*,
    # not a ClassVar.
    WG_CONFIG_PATH: Optional[Path] = None

    # ------------------------------------------------------------------
    # Connection‑pool
    # ------------------------------------------------------------------
    max_connection_count: int = 10
    min_connection_count: int = 10

    # ------------------------------------------------------------------
    # Hosts / CORS
    # ------------------------------------------------------------------
    allowed_hosts: List[str] = ["*"]

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    logging_level: int = logging.INFO
    loggers: Tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    # ------------------------------------------------------------------
    # Pydantic v2 settings
    # ------------------------------------------------------------------
    model_config: SettingsConfigDict = SettingsConfigDict(
        validate_assignment=True,
        extra="ignore",  # ignore unknown env vars
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @model_validator(mode="before")
    def _populate_wg_config_path(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Derive ``WG_CONFIG_PATH`` at runtime if it is missing."""
        if not values.get("WG_CONFIG_PATH"):
            interface = cls.WG_INTERFACE  # ClassVar
            cfg_dir = cls.WG_CONFIG_DIR
            values["WG_CONFIG_PATH"] = Path(cfg_dir) / f"{interface}.conf"
        else:
            values["WG_CONFIG_PATH"] = Path(values["WG_CONFIG_PATH"])
        return values

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def discovery_url(self) -> str:
        """Full URL of the discovery‑service endpoint."""
        return (
            f"http://{self.discovery_service_host}:{self.discovery_service_port}"
            "/api/v1.0/services"
        )

    @property
    def redis_url(self) -> str:
        """Assemble a Redis DSN."""
        if self.redis_user and self.redis_pass:
            return (
                f"redis://{self.redis_user}:{self.redis_pass}"  # noqa: S603
                f"@{self.redis_host}:{self.redis_port}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def fastapi_kwargs(self) -> Dict[str, Any]:
        """Parameters forwarded to ``FastAPI()`` ctor."""
        return {
            "debug": self.debug,
            "docs_url": self.docs_url,
            "openapi_prefix": self.openapi_prefix,
            "openapi_url": self.openapi_url,
            "redoc_url": self.redoc_url,
            "title": self.title,
            "version": self.version,
        }
