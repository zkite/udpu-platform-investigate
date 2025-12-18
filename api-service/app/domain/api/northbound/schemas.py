from __future__ import annotations

from enum import Enum

from typing import Optional
from uuid import uuid4

from datetime import datetime, timezone
from pydantic import BaseModel, Field

from utils.utils import (
    generate_pppoe_password,
    generate_pppoe_username,
    generate_udpu_hostname,
    get_provisioned_date,
)
from .constants import MAC_ADDRESS_KEY, UDPU_ENTITY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SubscriberUID = Field(default_factory=lambda: uuid4().hex[:16])

# ---------------------------------------------------------------------------
# Main entity
# ---------------------------------------------------------------------------

class Udpu(BaseModel):
    """Full subscriber record stored in Redis / DB."""

    subscriber_uid: str = SubscriberUID
    location: str
    mac_address: str = ""  # keep as str; can be empty until provisioned
    role: str
    upstream_qos: str
    downstream_qos: str
    hostname: str = Field(default_factory=generate_udpu_hostname)
    pppoe_username: str = Field(default_factory=generate_pppoe_username)
    pppoe_password: str = Field(default_factory=generate_pppoe_password)

    # -------------------- WireGuard parameters -----------------------
    wg_server_public_key: str = ""
    wg_interface: str = "wg0"
    wg_server_port: int = 51820
    wg_server_ip: str = ""
    wg_client_ip: str = ""
    wg_routes: str = ""
    wg_allowed_ips: str = ""
    endpoint: str = ""

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    # ------------------------------------------------------------------
    # Keys / Redis helpers
    # ------------------------------------------------------------------
    @property
    def subscriber_key(self) -> str:
        return f"{UDPU_ENTITY}:{self.subscriber_uid}"

    @property
    def mac_address_key(self) -> str:
        return f"{MAC_ADDRESS_KEY}:{self.mac_address}"


# ---------------------------------------------------------------------------
# Partial update (PATCH)
# ---------------------------------------------------------------------------

class UdpuUpdate(BaseModel):
    """Subset of fields allowed to be updated via API."""

    subscriber_uid: str = SubscriberUID
    location: Optional[str] = None
    mac_address: Optional[str] = None
    role: Optional[str] = None
    upstream_qos: Optional[str] = None
    downstream_qos: Optional[str] = None
    provisioned_last_date: str = Field(default_factory=get_provisioned_date)

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }

    @property
    def subscriber_key(self) -> str:
        return f"{UDPU_ENTITY}:{self.subscriber_uid}"

    @property
    def mac_address_key(self) -> str:
        mac = self.mac_address or ""
        return f"{MAC_ADDRESS_KEY}:{mac}"


# ---------------------------------------------------------------------------
# Devices that called home but are not yet registered
# ---------------------------------------------------------------------------

class UnregisteredDevice(BaseModel):
    subscriber_uid: str
    last_call_home_dt: str  # ISO 8601 string stored by backend
    ip_address: str

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }

class UdpuStatusEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

class UdpuStateEnum(str, Enum):
    REGISTERED = "registered"
    NOT_REGISTERED = "not_registered"
    UNKNOWN = "unknown"


class UdpuStatus(BaseModel):
    subscriber_uid: str
    state: Optional[str] = ""
    status: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))