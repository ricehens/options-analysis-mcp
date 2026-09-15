# Milestone 6L — Persistent Appearance Themes

Completed: 2026-09-14

## Outcome

The browser workspace supports system-selected, forced light, and forced dark
appearance modes. Three keyboard-operable buttons expose pressed state, apply
immediately, and persist the selection in browser-local storage. System is the
safe default for missing, invalid, or unavailable storage.

## Theme architecture

- Palette values live in semantic CSS custom properties rather than React
  components or feature selectors.
- Light is the base palette, explicit dark uses `data-theme="dark"`, and system
  dark uses `prefers-color-scheme` only when no explicit attribute exists.
- Charts, panels, tables, forms, selected states, warning/error surfaces, focus
  rings, overlays, and shadows consume the same semantic tokens.
- A small same-origin head script applies valid stored overrides before the
  application mounts, avoiding a visible wrong-theme render. The existing
  content security policy permits this external local script and still rejects
  inline scripts.
- `color-scheme: light dark` lets native controls follow the active palette.

The token boundary can support later accent or named-palette choices without
changing analysis components. Additional palettes remain a backlog item until
the owner has used the core modes and chooses a direction.

## Accessibility and verification

- Theme controls use native buttons inside a named group and expose
  `aria-pressed` for the selected mode.
- Automated checks cover normalization, persistence, invalid-value fallback,
  attribute application/removal, accessible server-rendered markup, pre-paint
  initialization, missing custom properties, and color literals outside token
  definitions.
- Core text, muted text, and accent foreground pairs meet at least 4.5:1 in the
  light and dark palettes.
- The production bundle exposes the initializer and light/dark browser chrome
  metadata successfully through the loopback HTTP server.
- The browser-control runtime failed before attaching in this session, so the
  owner visual confirmation remains explicitly tracked as `UI-055A`; no visual
  inspection is claimed.
- Full release-check evidence is recorded in `STATUS.md`.
