import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  addWatchlistSymbol,
  ApiError,
  deleteWatchlistSymbol,
  loadWatchlist,
  loadWorkspace,
} from "./api";
import type { DecimalValue, PutCall, Quote, WorkspaceSnapshot } from "./types";

const strategyNames = [
  "Single option",
  "Covered call",
  "Vertical spread",
  "Butterfly",
  "Iron condor",
];

function decimal(value: DecimalValue | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

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

interface ChainRow {
  strike: number;
  call?: Quote;
  put?: Quote;
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
      { expiration: expiration || undefined, putCall },
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
  }, [expiration, putCall, selectedSymbol]);

  const rows = useMemo(() => {
    const indexed = new Map<number, ChainRow>();
    for (const contract of workspace?.chain.contracts ?? []) {
      const terms = contract.instrument.option;
      if (!terms) continue;
      const strike = Number(terms.strike);
      const row = indexed.get(strike) ?? { strike };
      row[terms.put_call] = contract;
      indexed.set(strike, row);
    }
    return [...indexed.values()].sort((left, right) => left.strike - right.strike);
  }, [workspace]);

  async function addSymbol(event: FormEvent) {
    event.preventDefault();
    const normalized = symbolInput.trim().toUpperCase();
    if (!normalized) return;
    setWatchlistBusy(true);
    setWatchlistError(null);
    try {
      setSymbols(await addWatchlistSymbol(normalized));
      setSelectedSymbol(normalized);
      setExpiration("");
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
        setExpiration("");
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
    setExpiration("");
  }

  const quote = workspace?.quote;
  const asOf = quote
    ? new Intl.DateTimeFormat("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(quote.as_of))
    : "—";

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
            maxLength={8}
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
            <span className="status-dot" /> Offline-safe data
          </div>
        </header>

        {error || watchlistError ? (
          <div className="error-banner">{error ?? watchlistError}</div>
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
                    <option key={date} value={date}>{date}</option>
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

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th colSpan={3}>Calls</th>
                    <th className="strike-heading">Strike</th>
                    <th colSpan={3}>Puts</th>
                  </tr>
                  <tr className="subhead">
                    <th>Bid</th><th>Mark</th><th>Ask</th><th />
                    <th>Bid</th><th>Mark</th><th>Ask</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.strike}>
                      <td>{quoteCell(row.call, "bid")}</td>
                      <td>{quoteCell(row.call, "mark")}</td>
                      <td>{quoteCell(row.call, "ask")}</td>
                      <td className="strike">{money(row.strike)}</td>
                      <td>{quoteCell(row.put, "bid")}</td>
                      <td>{quoteCell(row.put, "mark")}</td>
                      <td>{quoteCell(row.put, "ask")}</td>
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
              <span className="coming-soon">Preview</span>
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
            <div className="analysis-preview">
              <span className="eyebrow">Selected template</span>
              <h3>{strategy}</h3>
              <p>
                Contract selection, combined Greeks, debit/credit, break-even,
                and payoff will appear here in the strategy-builder milestone.
              </p>
              <div className="metric-row">
                <div><span>Contracts</span><strong>{workspace?.chain.contracts.length ?? 0}</strong></div>
                <div><span>ATM IV</span><strong>{number(rows.find((row) => row.strike === 100)?.call?.implied_volatility, 2)}</strong></div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
