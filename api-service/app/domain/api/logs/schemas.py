from __future__ import annotations

from pydantic import BaseModel, Field

from domain.api.logs.constants import JOB_LOG_PREFIX


class JobLogSchema(BaseModel):
    """Immutable record produced by background job runner."""

    client:  str
    name: str = Field(..., description="Job name")
    command: str = Field(..., description="Executed shell command")
    std_err: str = ""
    std_out: str = ""
    status_code: str = ""
    timestamp: str = Field(..., description="ISO‑8601 UTC timestamp")

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    @property
    def key(self) -> str:  # noqa: D401
        return f"{JOB_LOG_PREFIX}:{self.client}:{self.name}:{self.timestamp}"
