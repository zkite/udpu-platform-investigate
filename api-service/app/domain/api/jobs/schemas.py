from __future__ import annotations

from enum import Enum
from typing import Optional, Union
from uuid import NAMESPACE_DNS, uuid5

from pydantic import BaseModel, Field, computed_field

from domain.api.jobs.constants import JOB_PREFIX


class JobFrequency(str, Enum):
    """Frequencies for jobs. String values match external inputs."""
    MIN_1 = "1"
    MIN_15 = "15"
    HOUR_1 = "60"
    HOUR_24 = "1440"
    FIRST_BOOT = "first_boot"
    EVERY_BOOT = "every_boot"
    ONCE = "once"

    @classmethod
    def parse(cls, value: Union[str, int]) -> "JobFrequency":
        s = str(value)
        try:
            return cls(s)
        except ValueError as exc:
            raise ValueError(f"Unknown job frequency: {value!r}") from exc


# ---------------------------------------------------------------------------
# Job — full definition stored in Redis / DB
# ---------------------------------------------------------------------------

class JobSchema(BaseModel):
    """Job definition supplied by admin UI / stored by backend."""

    name: str = Field(..., description="Human-readable job name")
    description: str = ""
    command: str = Field(..., description="Shell command to execute")
    require_output: str = ""
    required_software: str = ""
    frequency: Optional[JobFrequency] = Field(
        default=None,
        description='Execution frequency: "1","15","60","1440","first_boot","every_boot","once"',
    )
    locked: str = ""      # could be a bool flag later
    role: str = ""
    type: str = "common"   # e.g. common, vb-specific, etc.
    vbuser_id: str = ""

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    # ------------------------------------------------------------------
    # Derived fields
    # ------------------------------------------------------------------
    @computed_field
    def uid(self) -> str:  # noqa: D401
        """Deterministic UID derived from *name* (UUID-v5)."""
        return self._generate_uid(self.name)

    # ------------------------------------------------------------------
    # Redis / DB helper keys
    # ------------------------------------------------------------------
    @property
    def key(self) -> str:
        return f"{JOB_PREFIX}:{self.name}:{self.uid}"

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def serialize(self) -> dict:  # noqa: D401
        data = self.model_dump(exclude_none=True)
        data["uid"] = self.uid
        return data

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_uid(name: str) -> str:  # noqa: D401
        return uuid5(NAMESPACE_DNS, name).hex


# ---------------------------------------------------------------------------
# PATCH / update payload
# ---------------------------------------------------------------------------

class JobSchemaUpdate(BaseModel):
    """Subset of fields that can be patched via API."""

    description: Optional[str] = None
    command: Optional[str] = None
    require_output: Optional[str] = None
    required_software: Optional[str] = None
    frequency: Optional[JobFrequency] = None
    locked: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }
