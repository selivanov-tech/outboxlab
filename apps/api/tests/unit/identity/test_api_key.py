import uuid

from app.contexts.identity.domain.api_key import ApiKey, ApiKeyToken
from app.shared.util.clock import now


def test_issue_returns_a_token_whose_secret_is_only_stored_hashed() -> None:
    workspace_id = uuid.uuid7()

    key, token = ApiKey.issue(workspace_id)

    assert token.plaintext.startswith(f"olab_{key.prefix}_")
    assert key.workspace_id == workspace_id
    assert token.secret not in key.secret_hash
    assert len(key.secret_hash) == 64
    assert key.accepts(token)


def test_parse_round_trips_a_secret_that_contains_underscores() -> None:
    token = ApiKeyToken(prefix="a1b2c3d4e5f6", secret="abc_def-ghi")

    assert ApiKeyToken.parse(f"  {token.plaintext} ") == token


def test_parse_rejects_malformed_keys() -> None:
    for raw in ["", "olab", "olab_prefixonly", "other_a1b2_secret", "olab__secret"]:
        assert ApiKeyToken.parse(raw) is None


def test_a_wrong_secret_or_prefix_is_not_accepted() -> None:
    key, token = ApiKey.issue(uuid.uuid7())

    assert not key.accepts(ApiKeyToken(prefix=token.prefix, secret="guess"))
    assert not key.accepts(ApiKeyToken(prefix="000000000000", secret=token.secret))


def test_a_revoked_key_is_not_accepted() -> None:
    key, token = ApiKey.issue(uuid.uuid7())

    assert not key.model_copy(update={"revoked_at": now()}).accepts(token)
