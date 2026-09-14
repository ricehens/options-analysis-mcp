import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  addWatchlistSymbol,
  ApiError,
  deleteWatchlistSymbol,
  loadWatchlist,
  loadWorkspace,
} from "./api";
import {
  buildChainRows,
  daysToExpiration,
  decimal,
  filterChainRows,
  moneynessPercent,
  sortChainRows,
  spreadPercent,
} from "./chain";
import type {
  ChainFilters,
  MoneynessRange,
  SortDirection,
  SortKey,
} from "./chain";
import type { DecimalValue, PutCall, Quote, WorkspaceSnapshot } from "./types";

const strategyNames = [
  "Single option",
  "Covered call",
  "Vertical spread",
  "Butterfly",
  "Iron condor",
];

function money(value: DecimalValue | null | undefined): string {
  const parsed = decimal(value);
  return parsed === null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
      }).format(parsed);
}

function number(value: DecimalValue | null | undefined, digits = 2): string {
  const parsed = decimal(value);
  return parsed === null ? "—" : parsed.toFixed(digits);
}

function compact(value: number | null | undefined): string {
  return value === null || value === undefined
    ? "—"
    : Intl.NumberFormat("en-US", { notation: "compact" }).format(value);
}

function quoteCell(quote: Quote | undefined, field: "bid" | "ask" | "mark") {
  return quote ? money(quote[field]) : "—";
}

function spread(quote: Quote | undefined): string {
  const value = spreadPercent(quote);
  return value === null ? "—" : `${value.toFixed(1)}%`;
}

function percent(value: DecimalValue | null | undefined, digits = 1): string {
  const parsed = decimal(value);
  return parsed === null ? "—" : `${(parsed * 100).toFixed(digits)}%`;
}

interface DraftLeg {
  quote: Quote;
  action: "buy" | "sell";
  quantity: number;
}

function App() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("SPY");
  const [symbolInput, setSymbolInput] = useState("");
  const [expiration, setExpiration] = useState("");
  const [putCall, setPutCall] = useState<PutCall | "all">("all");
  const [strategy, setStrategy] = useState(strategyNames[0]);
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [watchlistBusy, setWatchlistBusy] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);
  const [strikeFromInput, setStrikeFromInput] = useState("");
  const [strikeToInput, setStrikeToInput] = useState("");
  const [strikeRange, setStrikeRange] = useState<{
    from?: number;
    to?: number;
  }>({});
  const [moneynessRange, setMoneynessRange] = useState<MoneynessRange>("all");
  const [minOpenInterest, setMinOpenInterest] = useState(0);
  const [maxSpreadPercent, setMaxSpreadPercent] = useState<number | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("strike");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [draftLegs, setDraftLegs] = useState<DraftLeg[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    loadWatchlist(controller.signal)
      .then((loadedSymbols) => {
        setSymbols(loadedSymbols);
        setSelectedSymbol((current) =>
          loadedSymbols.includes(current) ? current : (loadedSymbols[0] ?? ""),
        );
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setWatchlistError(
          reason instanceof Error ? reason.message : "Unable to load the watchlist.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setWatchlistBusy(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedSymbol) {
      setWorkspace(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    loadWorkspace(
      selectedSymbol,
      {
        expiration: expiration || undefined,
        putCall,
        strikeFrom: strikeRange.from,
        strikeTo: strikeRange.to,
      },
      controller.signal,
    )
      .then((snapshot) => {
        setWorkspace(snapshot);
        if (!expiration && snapshot.expirations.length) {
          setExpiration(snapshot.expirations[0]);
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        const message =
          reason instanceof ApiError || reason instanceof Error
            ? reason.message
            : "Unable to load market data.";
        setError(message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [expiration, putCall, selectedSymbol, strikeRange.from, strikeRange.to]);

  const rows = useMemo(() => {
    const filters: ChainFilters = {
      moneynessRange,
      minOpenInterest,
      maxSpreadPercent,
    };
    const paired = buildChainRows(workspace?.chain.contracts ?? []);
    return sortChainRows(
      filterChainRows(paired, decimal(workspace?.quote.mark), filters),
      sortKey,
      sortDirection,
    );
  }, [
    maxSpreadPercent,
    minOpenInterest,
    moneynessRange,
    sortDirection,
    sortKey,
    workspace,
  ]);

  const selectedContracts = useMemo(
    () => new Set(draftLegs.map((leg) => leg.quote.instrument.provider_symbol)),
    [draftLegs],
  );

  async function addSymbol(event: FormEvent) {
    event.preventDefault();
    const normalized = symbolInput.trim().toUpperCase();
    if (!normalized) return;
    setWatchlistBusy(true);
    setWatchlistError(null);
    try {
      setSymbols(await addWatchlistSymbol(normalized));
      setSelectedSymbol(normalized);
      resetSymbolWorkspace();
      setSymbolInput("");
    } catch (reason) {
      setWatchlistError(
        reason instanceof Error ? reason.message : "Unable to add the symbol.",
      );
    } finally {
      setWatchlistBusy(false);
    }
  }

  async function removeSymbol(symbol: string) {
    setWatchlistBusy(true);
    setWatchlistError(null);
    try {
      const remaining = await deleteWatchlistSymbol(symbol);
      setSymbols(remaining);
      if (selectedSymbol === symbol) {
        setSelectedSymbol(remaining[0] ?? "");
        resetSymbolWorkspace();
      }
    } catch (reason) {
      setWatchlistError(
        reason instanceof Error ? reason.message : "Unable to remove the symbol.",
      );
    } finally {
      setWatchlistBusy(false);
    }
  }

  function selectSymbol(symbol: string) {
    setSelectedSymbol(symbol);
    resetSymbolWorkspace();
  }

  function resetSymbolWorkspace() {
    setExpiration("");
    setDraftLegs([]);
    setStrikeFromInput("");
    setStrikeToInput("");
    setStrikeRange({});
    setFilterError(null);
  }

  function applyStrikeRange(event: FormEvent) {
    event.preventDefault();
    const from = strikeFromInput ? Number(strikeFromInput) : undefined;
    const to = strikeToInput ? Number(strikeToInput) : undefined;
    if (
      (from !== undefined && (!Number.isFinite(from) || from <= 0)) ||
      (to !== undefined && (!Number.isFinite(to) || to <= 0)) ||
      (from !== undefined && to !== undefined && from > to)
    ) {
      setFilterError("Enter a valid strike range with the lower value first.");
      return;
    }
    setFilterError(null);
    setStrikeRange({ from, to });
  }

  function changeSort(next: SortKey) {
    if (sortKey === next) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(next);
      setSortDirection("asc");
    }
  }

  function sortLabel(key: SortKey): string {
    return sortKey === key ? (sortDirection === "asc" ? " ↑" : " ↓") : "";
  }

  function toggleContract(contract: Quote | undefined) {
    if (!contract) return;
    const symbol = contract.instrument.provider_symbol;
    setDraftLegs((current) =>
      current.some((leg) => leg.quote.instrument.provider_symbol === symbol)
        ? current.filter((leg) => leg.quote.instrument.provider_symbol !== symbol)
        : [...current, { quote: contract, action: "buy", quantity: 1 }],
    );
  }

  function updateDraftLeg(
    symbol: string,
    update: Partial<Pick<DraftLeg, "action" | "quantity">>,
  ) {
    setDraftLegs((current) =>
      current.map((leg) =>
        leg.quote.instrument.provider_symbol === symbol ? { ...leg, ...update } : leg,
      ),
    );
  }

  const quote = workspace?.quote;
  const asOf = quote
    ? new Intl.DateTimeFormat("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(quote.as_of))
    : "—";
  const warningCount =
    (workspace?.chain.warnings.length ?? 0) +
    (workspace?.chain.contracts.reduce(
      (total, contract) => total + contract.warnings.length,
      0,
    ) ?? 0);
  const freshness =
    workspace?.provider_id === "fake"
      ? "Deterministic fixture"
      : quote
        ? `${Math.max(0, Math.round((Date.now() - Date.parse(quote.as_of)) / 1000))}s old`
        : "Waiting for data";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">OA</span>
          <div>
            <strong>Option Atlas</strong>
            <small>Research workspace</small>
          </div>
        </div>

        <div className="section-label">
          <span>Watchlist</span>
          <span>{watchlistBusy ? "…" : symbols.length}</span>
        </div>
        <form className="symbol-form" onSubmit={addSymbol}>
          <input
            aria-label="Add a stock symbol"
            autoComplete="off"
            maxLength={12}
            onChange={(event) => setSymbolInput(event.target.value)}
            placeholder="Add symbol"
            value={symbolInput}
          />
          <button aria-label="Add symbol" disabled={watchlistBusy} type="submit">
            +
          </button>
        </form>

        <nav className="watchlist" aria-label="Stock watchlist">
          {symbols.map((symbol) => (
            <div
              className={`watch-row ${selectedSymbol === symbol ? "active" : ""}`}
              key={symbol}
            >
              <button className="symbol-button" onClick={() => selectSymbol(symbol)}>
                <span>{symbol}</span>
                <small>{symbol === selectedSymbol ? money(quote?.mark) : "View"}</small>
              </button>
              <button
                aria-label={`Remove ${symbol}`}
                className="remove-button"
                disabled={watchlistBusy}
                onClick={() => removeSymbol(symbol)}
                title={`Remove ${symbol}`}
              >
                ×
              </button>
            </div>
          ))}
        </nav>

        <div className="connection-card">
          <span className="status-dot" />
          <div>
            <strong>{workspace?.provider_id ?? "Connecting"}</strong>
            <small>Read-only provider</small>
          </div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <span className="eyebrow">Market workspace</span>
            <h1>{selectedSymbol || "No symbol"}</h1>
          </div>
          <div className="market-status">
            <span className={`status-dot ${warningCount ? "warning" : ""}`} />
            {freshness} · {warningCount} warning{warningCount === 1 ? "" : "s"}
          </div>
        </header>

        {error || watchlistError || filterError ? (
          <div className="error-banner">{error ?? watchlistError ?? filterError}</div>
        ) : null}

        <section className={`quote-hero ${loading ? "loading" : ""}`}>
          <div>
            <span className="eyebrow">Underlying mark</span>
            <div className="hero-price">{money(quote?.mark)}</div>
            <span className="as-of">As of {asOf}</span>
          </div>
          <div className="quote-grid">
            <div><span>Bid</span><strong>{money(quote?.bid)}</strong></div>
            <div><span>Ask</span><strong>{money(quote?.ask)}</strong></div>
            <div><span>Last</span><strong>{money(quote?.last)}</strong></div>
            <div><span>Volume</span><strong>{compact(quote?.volume)}</strong></div>
          </div>
        </section>

        <section className="workspace-grid">
          <div className="panel chain-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Contract explorer</span>
                <h2>Option chain</h2>
              </div>
              <div className="filters">
                <select
                  aria-label="Expiration"
                  onChange={(event) => setExpiration(event.target.value)}
                  value={expiration}
                >
                  {(workspace?.expirations ?? []).map((date) => (
                    <option key={date} value={date}>
                      {date} · {daysToExpiration(date)} DTE
                    </option>
                  ))}
                </select>
                <div className="segmented" aria-label="Option side">
                  {(["all", "call", "put"] as const).map((side) => (
                    <button
                      className={putCall === side ? "selected" : ""}
                      key={side}
                      onClick={() => setPutCall(side)}
                    >
                      {side}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="filter-bar">
              <form className="strike-range" onSubmit={applyStrikeRange}>
                <label>
                  <span>Strike from</span>
                  <input
                    min="0"
                    onChange={(event) => setStrikeFromInput(event.target.value)}
                    placeholder="Any"
                    step="0.5"
                    type="number"
                    value={strikeFromInput}
                  />
                </label>
                <label>
                  <span>Strike to</span>
                  <input
                    min="0"
                    onChange={(event) => setStrikeToInput(event.target.value)}
                    placeholder="Any"
                    step="0.5"
                    type="number"
                    value={strikeToInput}
                  />
                </label>
                <button type="submit">Apply</button>
              </form>
              <label>
                <span>Moneyness</span>
                <select
                  onChange={(event) =>
                    setMoneynessRange(event.target.value as MoneynessRange)
                  }
                  value={moneynessRange}
                >
                  <option value="all">All strikes</option>
                  <option value="2.5">Within 2.5%</option>
                  <option value="5">Within 5%</option>
                  <option value="10">Within 10%</option>
                </select>
              </label>
              <label>
                <span>Minimum OI</span>
                <select
                  onChange={(event) => setMinOpenInterest(Number(event.target.value))}
                  value={minOpenInterest}
                >
                  <option value="0">Any</option>
                  <option value="100">100+</option>
                  <option value="500">500+</option>
                  <option value="1000">1,000+</option>
                </select>
              </label>
              <label>
                <span>Maximum spread</span>
                <select
                  onChange={(event) =>
                    setMaxSpreadPercent(
                      event.target.value ? Number(event.target.value) : null,
                    )
                  }
                  value={maxSpreadPercent ?? ""}
                >
                  <option value="">Any</option>
                  <option value="5">5%</option>
                  <option value="10">10%</option>
                  <option value="25">25%</option>
                </select>
              </label>
            </div>

            <div className="chain-meta">
              <span>{rows.length} strikes shown</span>
              <span>Click + to add a contract to the draft</span>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th colSpan={7}>Calls</th>
                    <th className="strike-heading">Strike</th>
                    <th colSpan={7}>Puts</th>
                  </tr>
                  <tr className="subhead">
                    <th /><th>Delta</th>
                    <th><button className="sort-button" onClick={() => changeSort("call_iv")}>IV{sortLabel("call_iv")}</button></th>
                    <th>Bid</th><th>Ask</th><th>Spread</th>
                    <th><button className="sort-button" onClick={() => changeSort("call_open_interest")}>OI{sortLabel("call_open_interest")}</button></th>
                    <th><button className="sort-button" onClick={() => changeSort("strike")}>Price{sortLabel("strike")}</button></th>
                    <th /><th>Delta</th>
                    <th><button className="sort-button" onClick={() => changeSort("put_iv")}>IV{sortLabel("put_iv")}</button></th>
                    <th>Bid</th><th>Ask</th><th>Spread</th>
                    <th><button className="sort-button" onClick={() => changeSort("put_open_interest")}>OI{sortLabel("put_open_interest")}</button></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.strike}>
                      <td>
                        {row.call ? (
                          <button
                            aria-label={`Toggle call at ${row.strike}`}
                            aria-pressed={selectedContracts.has(row.call.instrument.provider_symbol)}
                            className={`contract-picker ${selectedContracts.has(row.call.instrument.provider_symbol) ? "selected" : ""}`}
                            onClick={() => toggleContract(row.call)}
                          >+</button>
                        ) : null}
                      </td>
                      <td>{number(row.call?.greeks?.delta)}</td>
                      <td>{percent(row.call?.implied_volatility)}</td>
                      <td>{quoteCell(row.call, "bid")}</td>
                      <td>{quoteCell(row.call, "ask")}</td>
                      <td>{spread(row.call)}</td>
                      <td>{compact(row.call?.open_interest)}</td>
                      <td className="strike">
                        <strong>{money(row.strike)}</strong>
                        <small>
                          {moneynessPercent(row.strike, decimal(quote?.mark))?.toFixed(1) ?? "—"}%
                        </small>
                      </td>
                      <td>
                        {row.put ? (
                          <button
                            aria-label={`Toggle put at ${row.strike}`}
                            aria-pressed={selectedContracts.has(row.put.instrument.provider_symbol)}
                            className={`contract-picker ${selectedContracts.has(row.put.instrument.provider_symbol) ? "selected" : ""}`}
                            onClick={() => toggleContract(row.put)}
                          >+</button>
                        ) : null}
                      </td>
                      <td>{number(row.put?.greeks?.delta)}</td>
                      <td>{percent(row.put?.implied_volatility)}</td>
                      <td>{quoteCell(row.put, "bid")}</td>
                      <td>{quoteCell(row.put, "ask")}</td>
                      <td>{spread(row.put)}</td>
                      <td>{compact(row.put?.open_interest)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!loading && rows.length === 0 ? (
                <div className="empty-state">No contracts match these filters.</div>
              ) : null}
            </div>
          </div>

          <div className="panel strategy-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Position lab</span>
                <h2>Strategy setup</h2>
              </div>
              <span className="coming-soon">{draftLegs.length} legs</span>
            </div>
            <div className="strategy-list">
              {strategyNames.map((name) => (
                <button
                  className={strategy === name ? "active" : ""}
                  key={name}
                  onClick={() => setStrategy(name)}
                >
                  <span>{name}</span><span>→</span>
                </button>
              ))}
            </div>
            <div className="draft-tray">
              <div className="draft-heading">
                <span className="eyebrow">Selected contracts</span>
                {draftLegs.length ? (
                  <button onClick={() => setDraftLegs([])}>Clear</button>
                ) : null}
              </div>
              {draftLegs.length === 0 ? (
                <p className="draft-empty">
                  Select contracts with the + buttons in the chain.
                </p>
              ) : (
                draftLegs.map((leg) => {
                  const terms = leg.quote.instrument.option;
                  const symbol = leg.quote.instrument.provider_symbol;
                  return (
                    <div className="draft-leg" key={symbol}>
                      <div className="leg-contract">
                        <strong>{terms ? money(terms.strike) : symbol}</strong>
                        <small>
                          {terms?.expiration_date} {terms?.put_call}
                        </small>
                      </div>
                      <select
                        aria-label={`Action for ${symbol}`}
                        onChange={(event) =>
                          updateDraftLeg(symbol, {
                            action: event.target.value as "buy" | "sell",
                          })
                        }
                        value={leg.action}
                      >
                        <option value="buy">Buy</option>
                        <option value="sell">Sell</option>
                      </select>
                      <input
                        aria-label={`Quantity for ${symbol}`}
                        max="99"
                        min="1"
                        onChange={(event) =>
                          updateDraftLeg(symbol, {
                            quantity: Math.max(1, Number(event.target.value) || 1),
                          })
                        }
                        type="number"
                        value={leg.quantity}
                      />
                      <button
                        aria-label={`Remove ${symbol} from draft`}
                        className="leg-remove"
                        onClick={() => toggleContract(leg.quote)}
                      >×</button>
                    </div>
                  );
                })
              )}
            </div>
            <div className="analysis-preview">
              <span className="eyebrow">Selected template</span>
              <h3>{strategy}</h3>
              <p>
                Selected contracts are now retained as editable draft legs.
                Combined Greeks, debit/credit, break-even, and payoff arrive in
                the strategy-builder milestone.
              </p>
              <div className="metric-row">
                <div><span>Loaded</span><strong>{workspace?.chain.contracts.length ?? 0}</strong></div>
                <div><span>Selected</span><strong>{draftLegs.length}</strong></div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
