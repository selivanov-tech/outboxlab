import uuid

import pytest
from pydantic import ValidationError

from app.identity.domain.workspace import Workspace
from app.shared.util.clock import now


def _make_workspace(**overrides: object) -> Workspace:
    defaults = {
        "id": uuid.uuid7(),
        "name": "acme",
        "created_at": now(),
    }
    defaults.update(overrides)
    return Workspace(**defaults)


def test_workspace_is_frozen() -> None:
    ws = _make_workspace()
    with pytest.raises(ValidationError):
        ws.name = "renamed"  # type: ignore[misc]


def test_workspace_equality_by_value() -> None:
    ws_id = uuid.uuid7()
    created = now()
    a = _make_workspace(id=ws_id, name="acme", created_at=created)
    b = _make_workspace(id=ws_id, name="acme", created_at=created)
    assert a == b


def test_workspace_validates_uuid() -> None:
    with pytest.raises(ValidationError):
        Workspace(
            id="not-a-uuid",  # type: ignore[arg-type]
            name="acme",
            created_at=now(),
        )
