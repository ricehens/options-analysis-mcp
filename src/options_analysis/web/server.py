"""Local-only HTTP server entry point."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "options_analysis.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
