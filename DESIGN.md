# Provider-Pluggable Options Data and Analysis MCP — Design

Status: Browser strategy-analysis workflow implemented through Milestone 6I

Last updated: 2026-09-14

Target directory: /Users/xuemingshen/Workspaces/schwab

## 1. Goal

Build a small, secure, read-only options-data platform that can become the data
foundation for option-position analysis applications. Charles Schwab is the
first provider implementation, not an architectural dependency.

The first client interface is a local MCP server. The underlying code must also
be reusable later by:

- A desktop or web analysis application.
- Python notebooks and batch analysis.
- A local REST or WebSocket service.
- A different MCP host.

The system should make detailed current stock and option data easy to consume
without forcing application code to understand any provider's response shapes.

Provider portability is a first-class design goal and release criterion:

- Domain models, analytics, services, MCP schemas, and HTTP endpoints are
  provider-neutral.
- A provider is integrated behind small, capability-based contracts.
- Adding a comparable source should normally add an adapter package,
  configuration, fixtures, and contract tests only.
- Existing analysis code and MCP clients must not change when the configured
  provider changes.
- Provider-specific fields remain available through namespaced extensions so
  normalization does not reduce every source to a lowest common denominator.
- Every observation retains provider, timestamp, entitlement/freshness, and
  field-level provenance where sources or local calculations are mixed.

## 2. Product outcome

Given an underlying symbol or a set of option legs, a client should be able to:

- Retrieve the underlying quote.
- Discover expirations and option contracts.
- Retrieve a filtered option chain.
- Retrieve detailed quotes for selected option contracts.
- Normalize prices, implied volatility, Greeks, volume, open interest,
  multiplier, deliverables, settlement attributes, and timestamps.
- Accept user-supplied positions for analysis.
- Optionally retrieve account positions when the Schwab application is entitled
  to the read-only Trader API.
- Enrich positions with current market data.
- Aggregate position and portfolio Greeks.
- Generate expiration payoff and price/volatility/time scenario inputs.
- Identify stale, missing, crossed, or otherwise questionable data.

The initial project is an analysis data service. It is not a trading system.

## 3. Scope

### 3.1 Initial scope

- Python 3.12 or newer.
- Official Model Context Protocol Python SDK 2.x.
- Local stdio MCP transport and loopback HTTP interface.
- Schwab OAuth authorization-code flow.
- Secure local token persistence.
- Schwab Market Data Production endpoints.
- Optional read-only accounts and positions through Trader API Individual.
- Typed normalized models.
- Provider contracts, registry, capability discovery, and a deterministic fake
  provider for offline development.
- Schwab as the first built-in provider adapter.
- Structured MCP results suitable for code as well as language models.
- Offline tests with sanitized fixtures.
- Live smoke tests that must be invoked explicitly.

### 3.2 Explicit non-goals

- Placing, replacing, previewing, or cancelling orders.
- Automated trading.
- Multi-user hosting.
- Redistributing provider market data contrary to its license or entitlements.
- Historical option-chain storage or options backtesting.
- Treating provider-supplied Greeks as an authoritative independent risk model.
- Order-entry or account-mutation controls in the graphical interface.
- Running an always-on streaming service in the first release.
- A lowest-common-denominator abstraction that hides useful provider data.
- Automatic cross-provider fallback that silently mixes inconsistent snapshots.

### 3.3 Assumptions

- The Schwab developer application is already approved and Ready for Use.
- The application has Market Data Production enabled.
- The registered callback URL exactly matches local configuration.
- The user will complete a one-time browser authorization.
- Trader API access may or may not be enabled. The design works without it by
  accepting positions as tool input.
- Data is for the authorized user's personal, noncommercial analysis.

## 4. Architectural decision

MCP must remain a thin adapter. Business logic and concrete provider integration
logic must not live inside MCP tool functions.

    MCP stdio adapter       React browser
            |                    |
            |             FastAPI HTTP adapter
            |                    |
            +--------------------+
                     |
    Application services
       |           |
    Analytics   Provider router
       |           |
    Domain models  Provider contracts
                   |      |       |
                Schwab  Tradier  Other plug-ins
                   |
              OAuth and HTTP

The packages are planned as:

- options_analysis.domain — canonical contracts and value objects.
- options_analysis.providers — provider protocols, capabilities, registry, and
  routing.
- options_analysis.providers.schwab — OAuth, HTTP client, source response
  models, and mapping for the first provider.
- options_analysis.services — chain, quote, position-enrichment, and analysis
  use cases.
- options_analysis.analytics — aggregation, payoff, and scenario calculations.
- options_analysis.mcp — provider-neutral MCP schemas and tool handlers.
- options_analysis.web — local-only provider-neutral HTTP endpoints.
- options_analysis.storage — local persistence adapters behind service
  protocols; SQLite is the first implementation.
- ui — responsive React/TypeScript client containing no provider credentials.

This split allows a later application to import the services directly or put an
HTTP interface beside MCP without copying provider logic. Imports point inward:
provider adapters may depend on provider contracts and domain models; domain,
analytics, services, and MCP schemas never import a concrete adapter.

### 4.1 Provider contracts

Adapters implement only the contracts relevant to their capabilities:

- Provider — identity, version, health, capabilities, and safe configuration
  status.
- MarketDataProvider — underlying quotes, option expirations, option chains,
  and selected contract quotes.
- HistoricalDataProvider — time-bounded underlying or option history.
- PortfolioProvider — read-only accounts and positions.
- StreamingProvider — optional future quote subscriptions.

There is deliberately no ExecutionProvider in the read-only project.

Each adapter owns its authentication, rate-limit behavior, raw response models,
symbol translation, and mapping into canonical models. Services depend on the
contracts, not on HTTP or vendor SDKs.

Built-in providers are registered explicitly. External plug-ins may register a
factory through the Python entry-point group `options_analysis.providers`.
Installed plug-ins are not loaded merely because they exist: configuration must
allow-list and enable a provider identifier. Provider secrets are resolved by
the adapter's local configuration and never passed through discovery metadata
or MCP arguments.

### 4.2 Capabilities and routing

Capability identifiers include `underlying_quotes`, `option_expirations`,
`option_chains`, `option_quotes`, `provider_greeks`, `open_interest`,
`price_history`, `option_history`, `account_positions`, and later `streaming`.

Every generic MCP request accepts an optional provider identifier. If omitted,
the configured default for that capability is used. The router validates the
capability before making a request. A missing capability returns a structured
`unsupported_capability` result; it is not approximated or silently routed to a
different source.

Future composite routing may explicitly use one provider for positions and a
different provider for quotes or history. Such a request records each source
and as-of time and applies synchronization checks. It never presents mixed data
as a single-provider snapshot.

### 4.3 Portability acceptance constraint

Adding a provider with equivalent capabilities must not require changes to:

- Canonical domain and analysis result models.
- Analytics implementations.
- Existing MCP tool names or their provider-neutral fields.
- Application-service use cases.

Allowed changes are a new adapter package, provider registration/configuration,
sanitized fixtures, and documented capability-specific extensions. A shared
provider conformance suite verifies canonical mapping, errors, pagination,
timestamps, provenance, and data-quality behavior. Milestone 1 proves this
boundary with a deterministic fake provider before the Schwab adapter exists.

### 4.4 Practical future provider candidates

This is a compatibility shortlist, not a popularity ranking:

| Provider | Best fit in this design | Integration note |
| --- | --- | --- |
| Schwab | First live market-data and optional position adapter | OAuth-based; current project target. |
| Tradier | Straightforward second retail-broker adapter | Documents option chains, expirations, quotes, and option Greeks; account access can be a separate capability. |
| Alpaca | Retail/developer brokerage and snapshot data | Documents option-chain snapshots with latest trade, quote, and Greeks. |
| Interactive Brokers | Broad brokerage/account coverage | Powerful but more complex: option-chain discovery is multi-step and market data is session-, entitlement-, and pacing-sensitive. |
| Massive | Data-only live/historical enrichment | Chain snapshots can include quotes, IV, Greeks, and open interest depending on plan. |
| ORATS | Options analytics and historical research | Useful for enriched chains, proprietary analytics, screening, and backtesting rather than account positions. |
| Databento | High-fidelity live/historical OPRA research | Best treated as a historical/streaming adapter, not a retail portfolio source. |

For a second adapter, Tradier or Alpaca is the smallest proof of broker
portability. Massive or ORATS is a better proof that broker positions and richer
market data can come from different providers. Databento is a later candidate
when serious historical options research or backtesting enters scope.

Official capability references:

- Tradier market data: https://docs.tradier.com/docs/market-data
- Alpaca option-chain snapshot: https://docs.alpaca.markets/us/reference/optionchain
- Interactive Brokers option chains:
  https://ibkrcampus.com/docs/web-api/v1/endpoints/option-chains/introduction
- Massive option-chain snapshot:
  https://massive.com/docs/rest/options/snapshots/option-chain-snapshot
- ORATS API: https://orats.com/docs
- Databento equity options: https://databento.com/docs/quickstart

## 5. Data model

### 5.1 Instrument identity

Option symbols are useful external identifiers but are not sufficient as the
only internal identity. The normalized OptionContract model includes:

- provider
- provider_symbol
- canonical OCC symbol when one can be established
- underlying_symbol
- option_root
- expiration_date
- last_trading_datetime when supplied
- put_or_call
- strike
- multiplier
- deliverables
- exercise_style when known
- settlement_type when known
- standard_or_adjusted status

Numeric values representing money, strikes, quantities, or Greeks are parsed
through Decimal rather than binary floating point at API boundaries.

### 5.2 Quote

A normalized quote includes:

- instrument identity
- bid, ask, bid size, and ask size
- last and last size
- mark
- underlying price when supplied
- quote time and trade time
- receipt time
- volume and open interest
- implied volatility
- delta, gamma, theta, vega, and rho
- theoretical value when supplied
- exchange and security status
- source and data-quality flags
- field provenance for mixed or locally derived values
- namespaced provider_extensions for valuable noncanonical fields

The mapper preserves an optional raw payload for diagnostic use in memory.
Raw responses are not logged by default and are never written into test
fixtures without sanitization.

### 5.3 Positions

A PositionLeg includes:

- instrument
- signed quantity
- long_or_short
- average opening price when known
- current quote
- market value
- cost basis when available
- unrealized profit/loss when available
- source and as-of time

A PositionAnalysis includes:

- legs
- aggregate delta, gamma, theta, vega, and rho
- net market value
- net option premium or cost basis when known
- expiration payoff points
- maximum profit/loss only when mathematically bounded
- break-even estimates
- scenario grid
- warnings and missing-data indicators

Greeks are multiplied by signed contract quantity and contract multiplier.
Every result identifies its provider and whether each derived value came from a
provider field or was calculated locally.

## 6. MCP tools

Tool names are prefixed with `options_` to avoid collisions without coupling
clients to Schwab. Market-data tools accept an optional `provider`; the default
comes from server configuration.

### 6.1 Foundation tools

#### options_server_info

Returns server version, enabled feature groups, configured environment, and
whether live smoke tests are allowed. It never returns secrets or token values.

#### options_list_providers

Returns enabled provider identifiers, versions, capabilities, freshness modes,
and safe configuration status. It never returns secret configuration values.

#### options_provider_auth_status

For a selected provider, returns configured, authorized, token-expiry, and
reauthorization-required states when authentication applies. It may return
instructions but never credentials or tokens.

### 6.2 Market-data tools

#### options_get_underlying_quote

Input:

- symbol
- optional provider
- optional field set

Output:

- normalized quote
- source timestamps
- data-quality warnings

#### options_get_option_expirations

Input:

- underlying symbol
- optional provider

Output:

- expiration dates and days to expiration

#### options_get_option_chain

Input:

- underlying symbol
- optional provider
- call, put, or both
- from and to expiration dates
- strike count, exact strike, or strike range
- optional provider-specific parameters in a namespaced extension object
- include underlying quote
- include raw response, disabled by default

Output:

- normalized underlying quote
- normalized contracts grouped by expiration and strike
- chain metadata and warnings

The implementation applies conservative response-size limits. A caller must
explicitly request broad chains rather than accidentally returning the entire
chain.

#### options_get_option_quotes

Input:

- one or more option symbols
- optional provider

Output:

- normalized detailed quote for each contract
- per-symbol error and freshness information

#### options_get_price_history

This is for the underlying stock or index context, not historical option-chain
backtesting.

Input includes symbol, time range, resolution, and optional provider.

### 6.3 Position-analysis tools

#### options_analyze_positions

Accepts provider-neutral position legs supplied by the caller, enriches them
with current quotes from an optional selected provider, aggregates exposures,
and returns payoff/scenario data.

This tool works without Trader API access.

#### options_get_and_analyze_account_positions

Optional and disabled unless a read-only PortfolioProvider is configured, such
as Schwab Trader API access.

It retrieves selected account positions, filters or groups option legs, enriches
them with market data, and returns PositionAnalysis results. Account identifiers
are masked in MCP output unless explicitly needed to disambiguate accounts.

The account-position provider and market-data provider may be selected
separately. No account tool can mutate provider state.

## 7. Analytics boundary

### 7.1 First analytics

- Signed aggregate Greeks.
- Current bid, ask, midpoint, and mark valuation views.
- Expiration payoff for arbitrary option and underlying legs.
- Break-even roots.
- Bounded maximum profit and maximum loss detection.
- Scenario grid over underlying-price movement.

### 7.2 Later analytics

- Price/volatility/time three-dimensional scenarios.
- Recomputed implied volatility and Greeks using a documented model.
- Volatility surface and skew.
- Probability estimates.
- Early-exercise and dividend analysis.
- Strategy grouping and automatic spread recognition.

Provider-supplied Greeks are convenient market-data fields, but model
assumptions may not be completely specified. They must carry provider
provenance. Locally computed Greeks must identify model, interest-rate,
dividend, timestamp, and volatility inputs.

## 8. OAuth and secrets

- Application key and secret are read from environment variables or a local
  uncommitted secrets file.
- A template file documents required variable names without values.
- Tokens are stored outside the repository.
- Token replacement uses an atomic write.
- Token files use user-only permissions on POSIX systems.
- Logs redact authorization codes, application secrets, bearer tokens, refresh
  tokens, account numbers, and sensitive query parameters.
- The callback listener binds only to loopback.
- The authorization URL must be opened or copied by the user; automation never
  captures provider credentials.
- Reauthorization failure produces an actionable status rather than retrying
  indefinitely.

The default Schwab endpoint URLs are adapter configuration rather than core
constants. They must be checked against the application's current Schwab portal
documentation during first live activation; changing them does not affect
domain models, services, or MCP schemas.

No secret is accepted as an MCP tool argument because model-visible tool
arguments can be logged by clients.

## 9. Reliability and API behavior

- Centralized timeout, retry, and rate-limit policy.
- Retries only for safe read operations and transient failures.
- Exponential backoff with jitter and a bounded retry count.
- No retry for authentication, entitlement, or invalid-parameter failures.
- Maximum concurrency and response-size limits.
- Streaming is not used to evade request limits.
- Structured error categories: configuration, authorization, entitlement,
  validation, rate limit, upstream unavailable, upstream schema, and internal.
- Provider response parsing is strict enough to detect schema drift but tolerant
  of documented optional fields.

## 10. Data-quality rules

The result includes warnings when:

- Quote timestamps are missing or older than the configured freshness window.
- Bid exceeds ask.
- Both bid and ask are absent.
- Mark is outside a valid bid/ask market.
- Implied volatility or a Greek is absent.
- Open interest or volume is unavailable.
- The multiplier or deliverable is unusual.
- The option appears adjusted or nonstandard.
- The underlying quote and option quote are materially asynchronous.
- A provider returns partial results.
- Fields used together come from materially different as-of times or sources.

Warnings do not silently replace upstream values.

## 11. Technology choices

- Python 3.12+
- uv for environment and lockfile management
- MCP Python SDK 2.x, pinned to a tested compatible range
- Pydantic 2 for input, output, and configuration models
- HTTPX for asynchronous HTTP
- pytest, pytest-asyncio, respx, and hypothesis where property tests help
- Ruff for formatting and linting
- mypy or pyright for static checks

The official MCP Python SDK 2.x is the current stable line and supports stdio
and structured tool output. Reference:
https://github.com/modelcontextprotocol/python-sdk

Each provider's official documentation remains the authority for endpoints and
entitlements. Community packages may be consulted for field coverage, but the
project owns its authentication boundary, canonical mapping, and conformance
behavior.

## 12. Planned repository layout

    README.md
    DESIGN.md
    STATUS.md
    SECURITY.md
    pyproject.toml
    uv.lock
    .env.example
    .gitignore
    src/
      options_analysis/
        domain/
        providers/
          schwab/
        services/
        analytics/
        mcp/
    tests/
      unit/
      contract/
      fixtures/
      live/
    scripts/

## 13. Testing strategy

### 13.1 Offline tests

- Configuration validation.
- Provider registration, allow-listing, and capability routing.
- Deterministic fake-provider behavior.
- Shared provider conformance tests.
- Secret redaction.
- Token-store permissions and atomic replacement.
- OAuth state and callback validation.
- Request parameter serialization.
- Response mapping from sanitized fixtures.
- Option-chain filtering and output limits.
- Decimal handling.
- Greek aggregation.
- Payoff calculations and break-even roots.
- MCP tool schemas and structured results.
- Upstream error mapping.

Offline tests are the default and require no credential or network access.

### 13.2 Contract fixtures

Sanitized provider responses may be captured only through an explicit developer
workflow. Sanitization must remove account numbers, tokens, request identifiers,
and any other private data before a fixture is admitted. Fixtures are grouped by
provider and exercised through the shared conformance suite where applicable.

### 13.3 Live smoke tests

- Disabled unless an explicit environment flag is present.
- Read-only.
- Narrow symbol and strike scopes.
- Never run automatically in the normal test suite or continuous integration.

## 14. Milestones and pause points

Every milestone ends with:

- Updated STATUS.md.
- Test or inspection evidence.
- Changed-file summary.
- Known limitations.
- Exact next action.
- A pause for user review.

### Milestone 0 — Design and handoff documentation

Deliverables:

- README.md
- DESIGN.md
- STATUS.md

Acceptance:

- Goal and non-goals are explicit.
- MCP is separated from the reusable core.
- Provider portability and plug-in constraints are explicit.
- Market-data and position-analysis paths are designed.
- Security boundaries and milestones are documented.

### Milestone 1 — Offline project skeleton

Deliverables:

- Git repository and ignore rules.
- Python package and dependency configuration.
- Domain models, provider contracts, capability registry, and configuration.
- Deterministic fake provider used through application services.
- MCP server with `options_server_info` and `options_list_providers` only.
- Offline unit tests and developer commands.

Acceptance:

- Fresh environment can install from the lockfile.
- MCP server starts over stdio.
- Inspector or a small test client can list and call the two foundation tools.
- Fake-provider tests prove services do not import or require Schwab code.
- Provider conformance tests can be reused by future adapters.
- Tests, lint, and type checks pass.
- No secrets and no Schwab network calls.

### Milestone 2 — OAuth and Schwab read-only gateway

Deliverables:

- Authorization helper.
- Callback validation.
- Secure token store.
- Token refresh.
- HTTP gateway and typed error mapping.
- Schwab implementation of provider contracts.
- `options_provider_auth_status`.

Acceptance:

- Offline OAuth and token tests pass.
- User can complete authorization locally.
- A narrow authenticated read smoke test succeeds.
- No domain, analytics, service, or generic MCP schema change is needed to add
  the Schwab adapter.
- Secrets and tokens do not appear in logs or repository files.

### Milestone 3 — Option market-data tools

Deliverables:

- Stock quote.
- Option expirations.
- Filtered option chain.
- Detailed option quotes.
- Underlying price history.
- Normalized models and quality warnings.

Acceptance:

- Sanitized fixture tests cover normal, partial, empty, and error responses.
- MCP schemas enforce narrow defaults.
- The same service and MCP contracts work with the fake and Schwab providers.
- Live smoke tests succeed for one liquid underlying and a few contracts.

### Milestone 4 — Position enrichment and first analytics

Deliverables:

- Caller-supplied position input.
- Optional read-only Schwab account-position retrieval.
- Quote enrichment.
- Greek aggregation.
- Expiration payoff, break-even, and basic scenario grid.

Acceptance:

- Known strategy fixtures match hand-calculated results.
- Missing and stale data remain visible.
- Account mode is feature-gated and read-only.
- Derived values identify inputs and assumptions.

### Milestone 5 — Hardening and packaging

Deliverables:

- Full operating guide.
- Security guide.
- MCP host configuration examples.
- Provider plug-in developer guide and conformance-test instructions.
- Schema-drift diagnostics.
- Better retry, cache, and rate-limit behavior.
- Release/version process.

Acceptance:

- A separate session can set up and operate the project using repository docs.
- All offline quality checks pass from one documented command.
- Failure and reauthorization workflows are documented and tested.

### Milestone 6A — Browser foundation

Deliverables:

- Loopback FastAPI interface beside MCP.
- Combined selected-symbol workspace endpoint.
- Responsive React/Vite shell with session watchlist, quotes, and option chain.
- HTTP contract tests and frontend production build.

Acceptance:

- MCP and HTTP reuse application services without provider-specific UI logic.
- Browser receives no provider credentials or tokens.
- Fake-provider workspace works end to end through the Vite proxy.
- Python checks and frontend production build pass.

### Milestone 6B–6I — Browser analysis workflow

- 6B: SQLite-backed watchlist persistence. (complete)
- 6C: rich option-chain filters and contract selection. (complete)
- 6D: strategy templates, leg editing, payoff, and combined analytics.
  (complete)
- 6E: packaged same-origin browser delivery, security headers, responsive and
  accessibility hardening. (complete)
- 6F: protective stock strategies, short-put and volatility workflows, and
  multi-expiration call calendars/diagonals. (complete)
- 6G: locally persistent named strategy definitions with fresh quote
  rehydration. (complete)
- 6H: expandable chain, contract, underlying, and analysis warning details with
  affected-field provenance. (complete)
- 6I: keyboard-operable, browser-persisted typography scaling from 90% through
  130%, without replacing native browser zoom. (complete)

Owner-driven live Schwab validation is tracked independently as `LIVE-010`
through `LIVE-030` in `TODO.md` so UI packaging does not depend on credentials.

### Milestone 7 — Optional streaming

Deliverables:

- Level-one equity and option subscriptions.
- Bounded in-memory current-state cache.
- Reconnect and resubscribe behavior.
- Snapshot tools backed by the cache.

Acceptance:

- Disconnect and partial-update tests pass.
- Freshness is explicit.
- The stream cannot produce unbounded memory growth.

Streaming should begin only if polling latency is inadequate for the analysis
application.

## 15. Deferred product decisions

These do not block the first three milestones:

- Whether account positions should be fetched or always supplied by the app.
- Which provider should be implemented second as a portability proof.
- Which local valuation model to use beyond provider-supplied Greeks.
- Whether normalized snapshots need persistent storage.
- Whether streaming is necessary.

## 16. Definition of the first useful release

The first useful release is reached after Milestone 4. It lets an application or
MCP client submit or retrieve option positions, enrich them with detailed
current data from a configured provider (Schwab first), and receive consistent
exposure and payoff analysis without provider-specific client code.

It remains deliberately read-only.
