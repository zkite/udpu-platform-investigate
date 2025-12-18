from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, Field

from domain.api.authentication.constants import CLIENT_STAMP

_MAC_REGEX = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|^[0-9A-Fa-f]{12}$")

MacAddress = Annotated[
    str,
    Field(pattern=_MAC_REGEX.pattern, description="MAC address in XX:XX:XX:XX:XX:XX or XXXXXXXXXXXX form"),
]


class Stamp(BaseModel):
    mac_address: MacAddress
    body: str

    model_config = {
        "extra": "ignore",
        "validate_assignment": True,
    }

    @property
    def key(self) -> str:  # noqa: D401
        """Return storage key combining constant prefix and MAC."""
        return f"{CLIENT_STAMP}:{self.mac_address.lower()}"
