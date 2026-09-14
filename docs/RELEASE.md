# Release Checklist

1. Confirm the worktree contains no `.env`, token, private fixture, account ID,
   or captured provider response.
2. Update the version in `pyproject.toml` and
   `src/options_analysis/__init__.py` together.
3. Update `CHANGELOG.md`, `README.md`, `STATUS.md`, and the milestone note.
4. Run `make release-check` (or add `UV=.uv-bootstrap/bin/uv`).
5. Inspect wheel contents and confirm `options_analysis.testing` is packaged.
6. Start the built environment over stdio and call `options_server_info`.
7. Commit on a `codex/milestone-N` branch.
8. Create annotated tag `milestone-N`, push the branch and tag, then
   fast-forward `main` only after all checks pass.

Published package indexes and public releases are outside the current scope.
The private GitHub repository and milestone tags are the durable checkpoints.
