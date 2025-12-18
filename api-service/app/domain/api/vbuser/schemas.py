from __future__ import annotations


from typing import Dict, Optional

from pydantic import BaseModel, computed_field, field_validator

from utils.utils import get_vb_uid
from .constants import VBUSER_ENTITY


class VBUser(BaseModel):
    """Pydantic model representing a VBUser entity."""

    # ------------------------------------------------------------------
    # Primary identifiers
    # ------------------------------------------------------------------
    udpu: str
    ghn_interface: str
    lcmp_interface: str

    # ------------------------------------------------------------------
    # Optional metadata
    # ------------------------------------------------------------------
    location_id: Optional[str] = ""
    upstream_qos: Optional[str] = ""
    downstream_qos: Optional[str] = ""
    conf_ghn_profile: Optional[str] = ""
    seed_idx: Optional[int] = 0
    lq_min_rate: Optional[int] = 0
    lq_max_rate: Optional[int] = 0
    lq_current_rate: Optional[int] = 0
    force_local: Optional[str] = "false"
    ghn_password: Optional[str] = ""
    ghn_dm_mac: Optional[str] = ""
    ghn_ep_mac: Optional[str] = ""
    ghn_firmware: Optional[str] = ""
    ghn_profile: Optional[str] = ""

    # ------------------------------------------------------------------
    # Pydantic v2 config
    # ------------------------------------------------------------------
    model_config = {
        "extra": "ignore",  # ignore unexpected keys
        "validate_assignment": True,
    }

    # ------------------------------------------------------------------
    # Derived/computed attributes
    # ------------------------------------------------------------------
    @computed_field  # type: ignore[misc]  # (pydantic decorator)
    def vb_uid(self) -> str:  # noqa: D401
        """Return a stable UID composed of *udpu* and *ghn_interface*."""
        return get_vb_uid(self.udpu, self.ghn_interface)

    @property
    def key(self) -> str:
        """Redis/DB key for this VBUser."""
        return f"{VBUSER_ENTITY}:{self.vb_uid}"

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def serialize(self) -> Dict[str, str]:
        """Return *all* fields coerced to ``str`` — useful for Redis HMSET."""
        dumped = self.model_dump(exclude={"vb_uid"})  # computed not in dump
        return {k: str(v) for k, v in dumped.items()}

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("force_local", mode="before")
    @classmethod
    def parse_force_local(cls, v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            val = v.strip().lower()
            if val in {"true", "1", "yes", "false", "0", "no"}:
                return val
        raise ValueError("force_local must be bool or 'true'/'false'")
