"""OAuth token model and atomic user-only local persistence."""

import json
import os
import stat
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, field_validator

from options_analysis.domain._base import require_aware_datetime
from options_analysis.providers.errors import ProviderAuthorizationError


class OAuthToken(BaseModel):
    """In-memory token values whose repr and normal serialization are redacted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: SecretStr
    refresh_token: SecretStr | None = None
    token_type: str = "Bearer"
    scope: str | None = None
    expires_at: datetime
    refresh_token_expires_at: datetime | None = None

    @field_validator("expires_at", "refresh_token_expires_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_aware_datetime(value)

    def access_is_expiring(
        self, now: datetime, *, skew: timedelta = timedelta(seconds=60)
    ) -> bool:
        return self.expires_at <= now + skew

    def refresh_is_expired(self, now: datetime) -> bool:
        return self.refresh_token is None or (
            self.refresh_token_expires_at is not None
            and self.refresh_token_expires_at <= now
        )

    def persistent_dict(self) -> dict[str, str | None]:
        return {
            "access_token": self.access_token.get_secret_value(),
            "refresh_token": (
                self.refresh_token.get_secret_value() if self.refresh_token else None
            ),
            "token_type": self.token_type,
            "scope": self.scope,
            "expires_at": self.expires_at.isoformat(),
            "refresh_token_expires_at": (
                self.refresh_token_expires_at.isoformat()
                if self.refresh_token_expires_at
                else None
            ),
        }

    @classmethod
    def from_persistent_dict(cls, data: object) -> Self:
        if not isinstance(data, dict):
            raise ValueError("token document must be an object")
        return cls.model_validate(data)


class TokenStore:
    """Persist one token document atomically with POSIX user-only permissions."""

    def __init__(self, path: Path) -> None:
        self.path = Path(os.path.abspath(path.expanduser()))

    def load(self) -> OAuthToken | None:
        if not self.path.exists():
            return None
        self._validate_existing_file()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return OAuthToken.from_persistent_dict(data)
        except (OSError, ValueError, ValidationError) as error:
            raise ProviderAuthorizationError(
                "Stored Schwab authorization is unreadable; authorize again.",
                reauthorization_required=True,
            ) from error

    def save(self, token: OAuthToken) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self.path.parent, 0o700)
        if self.path.exists() or self.path.is_symlink():
            self._validate_existing_file()

        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
            )
            if os.name == "posix":
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(token.persistent_dict(), stream, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, self.path)
            temporary_name = None
            if os.name == "posix":
                os.chmod(self.path, 0o600)
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    def _validate_existing_file(self) -> None:
        file_stat = self.path.lstat()
        if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
            raise ProviderAuthorizationError(
                "Schwab token path must be a regular file, not a link.",
                reauthorization_required=True,
            )
        if os.name == "posix" and file_stat.st_mode & 0o077:
            raise ProviderAuthorizationError(
                "Schwab token file permissions are not user-only (expected 0600).",
                reauthorization_required=True,
            )
