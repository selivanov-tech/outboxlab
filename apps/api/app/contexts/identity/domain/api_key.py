import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.shared.util.clock import now

KEY_SCHEME = "olab"
_PREFIX_BYTES = 6
_SECRET_BYTES = 32


@dataclass(frozen=True)
class ApiKeyToken:
    prefix: str
    secret: str

    @property
    def plaintext(self) -> str:
        return f"{KEY_SCHEME}_{self.prefix}_{self.secret}"

    @classmethod
    def parse(cls, raw: str) -> "ApiKeyToken | None":
        scheme, _, rest = raw.strip().partition("_")
        prefix, _, secret = rest.partition("_")
        if scheme != KEY_SCHEME or not prefix or not secret:
            return None
        return cls(prefix=prefix, secret=secret)


class ApiKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    workspace_id: UUID
    prefix: str
    secret_hash: str
    created_at: datetime
    revoked_at: datetime | None

    @classmethod
    def issue(cls, workspace_id: UUID) -> tuple["ApiKey", ApiKeyToken]:
        token = ApiKeyToken(
            prefix=secrets.token_hex(_PREFIX_BYTES),
            secret=secrets.token_urlsafe(_SECRET_BYTES),
        )
        key = cls(
            id=uuid.uuid7(),
            workspace_id=workspace_id,
            prefix=token.prefix,
            secret_hash=_hash(token.secret),
            created_at=now(),
            revoked_at=None,
        )
        return key, token

    def accepts(self, token: ApiKeyToken) -> bool:
        return (
            self.revoked_at is None
            and self.prefix == token.prefix
            and hmac.compare_digest(self.secret_hash, _hash(token.secret))
        )


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()
