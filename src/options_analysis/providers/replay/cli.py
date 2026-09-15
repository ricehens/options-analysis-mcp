"""Command-line creation of a safe synthetic replay bundle."""

import argparse
import asyncio
import os
import tempfile
from pathlib import Path

from options_analysis.providers.replay.sample import create_sample_bundle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a synthetic options-analysis replay bundle."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument(
        "--force", action="store_true", help="replace an existing output file"
    )
    return parser


async def _write_sample(output: Path, symbol: str, *, force: bool) -> None:
    resolved = output.expanduser().resolve()
    if not resolved.parent.is_dir():
        raise ValueError("output parent directory does not exist")
    if resolved.exists() and not force:
        raise FileExistsError("output exists; pass --force to replace it")

    bundle = await create_sample_bundle(symbol)
    encoded = bundle.model_dump_json(indent=2).encode("utf-8")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{resolved.name}.", dir=resolved.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, resolved)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> None:
    parser = _parser()
    arguments = parser.parse_args()
    try:
        asyncio.run(
            _write_sample(arguments.output, arguments.symbol, force=arguments.force)
        )
    except (FileExistsError, OSError, ValueError) as error:
        parser.error(str(error))
    print(
        f"Created synthetic replay bundle at {arguments.output.expanduser().resolve()}"
    )


if __name__ == "__main__":
    main()
