from typing import Optional

from pydantic import BaseModel, computed_field
from uuid import uuid5, NAMESPACE_DNS
from domain.api.jobs.queues.constants import QUEUE_PREFIX


class JobQueueSchema(BaseModel):
    name: str
    description: Optional[str] = ""
    queue: str
    role: Optional[str] = ""
    require_output: Optional[str] = ""
    locked: Optional[str] = ""
    frequency: Optional[str] = ""

    @property
    def key(self):
        return f"{QUEUE_PREFIX}:{self.name}:{self.uid}"

    @computed_field
    @property
    def uid(self) -> str:
        return self._generate_uid(self.name)

    def serialize(self) -> dict:
        data = self.model_dump()
        data["uid"] = self.uid
        return data

    @staticmethod
    def _generate_uid(name):
        return uuid5(NAMESPACE_DNS, name).hex