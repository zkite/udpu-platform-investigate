from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from domain.api.roles.constants import ROLE_PREFIX

# ---------------------------------------------------------------------------
# Nested structures
# ---------------------------------------------------------------------------

class ManagementVlan(BaseModel):
    interface: str = "br-lan"


class GhnPort(BaseModel):
    ghn_interface: str = "1/0"
    lcmp_interface: str = "1/0.4098"
    vb: bool = False


class Interface(BaseModel):
    management_vlan: ManagementVlan = Field(default_factory=ManagementVlan)
    ghn_ports: List[GhnPort] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Main role schemas
# ---------------------------------------------------------------------------

class UdpuRole(BaseModel):
    name: str
    description: str
    wireguard_tunnel: bool = False
    job_control: bool = False
    interfaces: Interface = Field(default_factory=Interface)

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    # redis / db key helpers
    @property
    def key(self) -> str:
        return f"{ROLE_PREFIX}:{self.name}"


class UdpuRoleUpdate(BaseModel):
    name: str
    description: str
    wireguard_tunnel: bool = False
    job_control: bool = False

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    @property
    def key(self) -> str:
        return f"{ROLE_PREFIX}:{self.name}"


class UdpuRoleClone(BaseModel):
    name: str
    new_role_name: str

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    @property
    def key(self) -> str:
        return f"{ROLE_PREFIX}:{self.name}"

    @property
    def new_role_key(self) -> str:
        return f"{ROLE_PREFIX}:{self.new_role_name}"
