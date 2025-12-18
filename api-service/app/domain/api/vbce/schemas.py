from __future__ import annotations

import ipaddress
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .constants import VBCE_ENTITY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BOOL_STR_TRUE = {"true", "1", "yes", "True"}
_BOOL_STR_FALSE = {"false", "0", "no", "False"}


def _parse_bool(v): # noqa: ANN001
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        val = v.strip().lower()
        if val in _BOOL_STR_TRUE:
            return "true"
        if val in _BOOL_STR_FALSE:
            return "false"
    raise ValueError("must be a boolean or a 'true'/'false'‑like string")


# ---------------------------------------------------------------------------
# Main entity
# ---------------------------------------------------------------------------

class Vbce(BaseModel):
    name: str = Field(..., description="Unique VBCE identifier")
    description: Optional[str] = ""
    max_users: int = 510
    current_users: int = 0
    available_users: int = 0
    ip_address: str = ""
    tcp_port: str = ""
    location_id: str = ""
    is_empty: str = "false"
    is_full: str = "false"
    force_local: str = "false"
    lq_min_rate: int = 0
    lq_max_rate: int = 0
    lq_mean_rate: int = 0
    seed_idx_used: str = ""

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    # ------------------------------------------------------------------
    # Derived props
    # ------------------------------------------------------------------
    @property
    def key(self) -> str:
        return f"{VBCE_ENTITY}:{self.name}"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("is_empty", "is_full", "force_local", mode="before")
    @classmethod
    def _bool_like(cls, v):  # noqa: D401, ANN001
        return _parse_bool(v)

    @field_validator("ip_address", mode="before")
    @classmethod
    def _valid_ip(cls, v):  # noqa: D401, ANN001
        if v:
            try:
                ipaddress.ip_address(v)
            except ValueError as exc:
                raise ValueError("Invalid IP address") from exc
        return v

    @field_validator("tcp_port", mode="before")
    @classmethod
    def _valid_port(cls, v):  # noqa: D401, ANN001
        if v:
            if not v.isdigit() or not (0 <= int(v) <= 65535):
                raise ValueError("Invalid TCP port")
        return v

    @field_validator("max_users", mode="before")
    @classmethod
    def _non_negative(cls, v):  # noqa: D401, ANN001
        if v is not None and int(v) < 0:
            raise ValueError("max_users cannot be negative")
        return int(v)


# ---------------------------------------------------------------------------
# PATCH / update payload
# ---------------------------------------------------------------------------

class VbceUpdate(BaseModel):
    max_users: Optional[int] = Field(default=None, ge=0)
    ip_address: Optional[str] = None
    tcp_port: Optional[str] = None
    location_id: Optional[str] = None
    force_local: Optional[str] = None

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }

    # ----------------------- validators -------------------------------
    @field_validator("ip_address", mode="before")
    @classmethod
    def _valid_ip(cls, v):  # noqa: D401, ANN001
        if v:
            try:
                ipaddress.ip_address(v)
            except ValueError as exc:
                raise ValueError("Invalid IP address") from exc
        return v

    @field_validator("tcp_port", mode="before")
    @classmethod
    def _valid_port(cls, v):  # noqa: D401, ANN001
        if v:
            if not v.isdigit() or not (0 <= int(v) <= 65535):
                raise ValueError("Invalid TCP port")
        return v

    @field_validator("force_local", mode="before")
    @classmethod
    def _bool_like(cls, v):  # noqa: D401, ANN001
        if v is None:
            return v
        return _parse_bool(v)
