"""User-controlled local Schwab authorization and smoke-test commands."""

import argparse
import asyncio
import getpass
import json
import webbrowser

from options_analysis.config import AppSettings
from options_analysis.providers.errors import ProviderError
from options_analysis.providers.schwab import build_schwab_provider


async def _authorize(no_open: bool) -> int:
    settings = AppSettings()
    provider = build_schwab_provider(settings)
    request = provider.authorization_request()
    print("Open this URL and authorize the local application:\n")
    print(request.url)
    if not no_open:
        webbrowser.open(request.url)
    callback = getpass.getpass("\nPaste the full callback URL (input is hidden): ")
    await provider.complete_authorization(callback, request.state)
    print("Authorization stored in the configured user-only token file.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorize the Schwab adapter")
    parser.add_argument(
        "--no-open", action="store_true", help="Do not open the system browser"
    )
    arguments = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_authorize(arguments.no_open)))
    except ProviderError as error:
        parser.exit(2, f"Authorization failed: {error}\n")


async def _smoke(symbol: str) -> int:
    settings = AppSettings()
    if not settings.allow_live_smoke_tests:
        raise ProviderError(
            "Set OPTIONS_ANALYSIS_ALLOW_LIVE_SMOKE_TESTS=true to opt in."
        )
    provider = build_schwab_provider(settings)
    result = await provider.smoke_read(symbol)
    print(json.dumps(result, indent=2))
    return 0


def smoke_main() -> None:
    parser = argparse.ArgumentParser(description="Run one read-only Schwab API read")
    parser.add_argument("--symbol", default="SPY")
    arguments = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_smoke(arguments.symbol)))
    except ProviderError as error:
        parser.exit(2, f"Smoke test failed: {error}\n")
