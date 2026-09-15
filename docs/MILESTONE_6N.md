# Milestone 6N — Short-Term SMA 10 Overlay

Completed: 2026-09-14

## Outcome

The underlying-price panel now offers SMA 10 alongside SMA 20 and SMA 50. All
three overlays are requested together and can be shown or hidden independently.
SMA 10 is the curated short-term default because it is less noisy than SMA 5
while still responding faster than the existing medium-term SMA 20.

No new calculator type, endpoint, schema, or provider integration was needed.
The Milestone 6M `sma:<window>` implementation already accepts both `sma:5` and
`sma:10`; this checkpoint adds SMA 10 to the standard browser controls and to
the discovery examples.

## Presentation

- SMA 10 has its own semantic, theme-aware indicator color.
- The existing accessible pressed-state control group includes the new overlay.
- Chart bounds include only overlays that are currently visible.
- The same period semantics apply: ten selected-resolution closing bars.

## Verification

Full release verification and final counts are recorded in `STATUS.md`. The
frontend tests assert the curated request set and rendered SMA 10 control. The
shared Python catalog tests assert that HTTP and MCP advertise `sma:10`.
