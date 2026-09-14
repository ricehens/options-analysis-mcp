"""Secret-safe configuration owned by the Schwab adapter."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr

from options_analysis.config import AppSettings


class SchwabConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    client_id: SecretStr | None
    client_secret: SecretStr | None
    redirect_uri: str
    authorization_url: str
    token_url: str
    market_data_base_url: str
    token_path: Path
    http_timeout_seconds: float
    http_max_attempts: int
    http_max_response_bytes: int = 5_000_000

    @property
    def configured(self) -> bool:
        return self.client_id is not None and self.client_secret is not None

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "SchwabConfig":
        return cls(
            client_id=settings.schwab_client_id,
            client_secret=settings.schwab_client_secret,
            redirect_uri=settings.schwab_redirect_uri,
            authorization_url=settings.schwab_authorization_url,
            token_url=settings.schwab_token_url,
            market_data_base_url=settings.schwab_market_data_base_url,
            token_path=settings.schwab_token_path or default_token_path(),
            http_timeout_seconds=settings.schwab_http_timeout_seconds,
            http_max_attempts=settings.schwab_http_max_attempts,
            http_max_response_bytes=settings.schwab_http_max_response_bytes,
        )


def default_token_path() -> Path:
    """Return a per-user token path outside the source repository."""

    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "options-analysis-mcp"
        / "schwab-token.json"
    )
