from __future__ import annotations

import ipaddress

from typing import List, Optional, Annotated
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Regex‑validated aliases
# ---------------------------------------------------------------------------

BASE64_KEY_PATTERN = r"^[A-Za-z0-9+/=]{44}$"
Base64Key = Annotated[
    str,
    Field(pattern=BASE64_KEY_PATTERN, description="WireGuard base64 key (44 chars)"),
]

# ---------------------------------------------------------------------------
# Basic interface status
# ---------------------------------------------------------------------------

class InterfaceStatus(BaseModel):
    """State of a WireGuard interface as returned by the backend."""

    interface: str
    active: str

# ---------------------------------------------------------------------------
# CRUD payloads for peers
# ---------------------------------------------------------------------------

class PeerRemove(BaseModel):
    """Request body to remove a peer by its public key."""

    public_key: Base64Key = Field(..., description="Public key of the peer in Base64")


class Peer(BaseModel):
    """Full peer representation or creation payload."""

    public_key: Base64Key

    endpoint: Optional[str] = Field(
        default=None,
        description="host:port pair – omit if peer initiates first",
        examples=["203.0.113.5:51820"],
    )

    persistent_keepalive: Optional[int] = Field(default=25, ge=0, le=120)

    allowed_ips: List[str] = Field(
        ...,
        description="List of IP(/CIDR) strings, e.g. ['10.66.1.10/32', '10.250.0.0/16']",
        examples=[["10.66.1.10/32", "10.250.0.0/16"]],
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("allowed_ips", mode="after")
    def validate_ips(cls, ips: List[str]) -> List[str]:
        """Ensure every entry is a valid IP or CIDR."""
        for ip in ips:
            try:
                ipaddress.ip_network(ip, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid IP/CIDR: {ip}") from exc
        return ips

    @property
    def allowed_ips_str(self) -> str:
        """Comma‑separated form ready for `wg set … allowed-ips`."""
        return ",".join(self.allowed_ips)

