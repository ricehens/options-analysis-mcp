import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from options_analysis.providers.errors import ProviderAuthorizationError
from options_analysis.providers.schwab.tokens import OAuthToken, TokenStore


def token() -> OAuthToken:
    return OAuthToken(
        access_token="access-secret",
        refresh_token="refresh-secret",
        expires_at=datetime(2026, 9, 14, tzinfo=UTC),
    )


def test_token_store_is_atomic_private_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "private" / "token.json"
    store = TokenStore(path)

    store.save(token())
    loaded = store.load()

    assert loaded is not None
    assert loaded.access_token.get_secret_value() == "access-secret"
    assert path.read_text().count("access-secret") == 1
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
    assert list(path.parent.glob(f".{path.name}.*")) == []


def test_token_store_rejects_symlink(tmp_path: Path) -> None:
    actual = tmp_path / "actual.json"
    actual.write_text("{}")
    link = tmp_path / "token.json"
    link.symlink_to(actual)

    with pytest.raises(ProviderAuthorizationError, match="regular file"):
        TokenStore(link).load()
