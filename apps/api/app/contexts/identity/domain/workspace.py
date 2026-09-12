import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now


class Workspace(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    created_at: datetime

    @classmethod
    def new(cls, name: str) -> "Workspace":
        return cls(
            id=uuid.uuid7(),
            name=name,
            created_at=now(),
        )
