# Milestone 6E — Packaged Browser Delivery

Completed in code: 2026-09-14

## Delivered

- Vite now writes the production React bundle into
  `src/options_analysis/web/static`, which Hatch includes in the Python wheel.
- `options-analysis-web` serves both `/api/...` and the single-page application
  from one loopback process at `http://127.0.0.1:8000`.
- `GET /api/v1/info` reports whether the packaged frontend is available.
- Browser responses add a same-origin content security policy, no-referrer
  policy, MIME-sniffing protection, and framing denial.
- The UI includes a skip link, semantic status/error announcements, visible
  keyboard focus, sortable-column state, accessible table captions, and
  explicit button types.
- Touch targets and mobile form sizing were strengthened, destructive controls
  remain visible on touch devices, and reduced-motion preferences are honored.
- A local-only web-app manifest and vector icon provide install metadata without
  claiming offline support or adding a service worker.

## Runtime and packaging contract

`make web-build` replaces the packaged static directory. `make web-api` then
serves the resulting files and the provider-neutral API from the same origin.
Vite remains available through `make web-ui` only for development.

If the static index is absent, the API still starts, reports
`frontend_available: false`, and does not mount a root file server. API routes
are registered before the root mount so they cannot be shadowed by the SPA.

The service remains loopback-only, single-user, and read-only. The manifest is
not authorization to expose it on a LAN or the internet; that requires the
separate `MOB-010` and `MOB-020` decisions in `TODO.md`.

## Verification

- Ruff formatting and linting pass.
- Strict mypy passes across 52 source files.
- All 63 Python tests pass, including bundled-static and security-header tests.
- All nine TypeScript tests pass and the Vite production build succeeds.
- An isolated environment installed from the built wheel, started the
  `options-analysis-web` entry point, returned HTTP 200 for `/`, and reported
  version `0.6.4` with `frontend_available: true`; the source-environment check
  also returned the expected security headers.
- The release wheel was inspected for the FastAPI module, production HTML,
  manifest, icon, JavaScript, and CSS assets.

Automated in-app browser setup was unavailable in this session, so desktop and
narrow-viewport visual inspection remains explicitly blocked as `UI-011` in
`TODO.md`; it is not silently treated as completed.

## Next work

There is no active implementation item after this checkpoint. A future session
should select the next product priority in `TODO.md`. Likely choices are richer
strategy templates (`UI-050`), saved drafts (`UI-051`), owner-driven Schwab
activation (`LIVE-010`), or a second-provider decision (`DATA-010`).
