# Experimental distribution assumptions lab

This experiment is intentionally isolated on `eshen/distribution-lab`. It is
not part of the main workbench and makes no real-world probability or trading
recommendation claim. Its purpose is to expose how strongly payoff assessments
depend on an explicitly chosen terminal price distribution.

## Run the synthetic example

```sh
uv sync --all-groups
uv run options-analysis-distribution-lab examples/distribution-lab.json \
  --output-dir /tmp/my-distribution-report
```

Or use `python -m options_analysis.experiments.distribution` with the same
arguments. The output directory must not already exist. Open `report.html`
in a browser; `result.json` includes validated input, assumptions, results,
and limitations. Reports use no scripts, network resources, or external fonts;
user-controlled HTML text is escaped. Wide tables scroll on small screens
and are keyboard focusable.

Input JSON contains `position` (the existing `ManualResearchRequest` contract)
and `assumptions` (one through twelve uniquely named distribution scenarios).
Each scenario requires `name`, `measure`, `annual_drift`, `annual_volatility`.

`measure` is explicitly `subjective` or `risk_neutral`. Both drift and
volatility are required annual decimals. No distribution volatility is
inferred from option IV, and no success probability is inferred from delta.
For the `risk_neutral` label, supplied drift must equal the position's entered
risk-free rate minus continuous dividend yield. That is a consistency check,
not a real-world expected return. Subjective drift is an unverified user
assumption. Drift means expected **price** growth excluding dividend cash.

The position must contain at least one option and exactly one shared expiry.
Only standard share-deliverable options are supported; shares can accompany
them. Current marks, option IV, calibration, horizon, and scenario IV shifts
are unused here. Entry prices, signed quantities, multipliers, spot, dates,
and round-trip fees determine terminal P/L.

## Calculation

Each output includes probabilities of strictly positive P/L, loss, and exactly
zero P/L separately; expected terminal underlying price, position value and
undiscounted P/L; and integrated mass as a normalization diagnostic. Zero time
or volatility produces a deterministic terminal price and outcome.

```
S(T) = S(0) exp((mu - sigma^2 / 2) T + sigma sqrt(T) Z)
Z ~ Normal(0, 1), T = calendar days / 365
```

Strikes partition P/L into intervals on which it is `a*S + b`. Break-even
roots partition these into profitable, losing, and flat-zero regions. The
infinite upper tail is included analytically. Let
`m = log(S0) + (mu - sigma^2/2)*T`, `s = sigma*sqrt(T)`, and
`z(x) = (log(x)-m)/s`. Integration uses:

```
P(L < S < U) = Phi(z(U)) - Phi(z(L))
E[S 1(L<S<U)] = S0 exp(mu*T) [Phi(z(U)-s) - Phi(z(L)-s)]
E[(a*S+b) 1(L<S<U)] = a E[S 1(L<S<U)] + b P(L<S<U)
```

The truncated first-moment identity follows by completing the square in the
normal density. Complementary-error-function differences avoid tail
cancellation. Decimal arithmetic preserves slopes and roots; normal
probabilities and moments use double precision. Tiny accumulated mass
roundoff is normalized. A deterministic payoff exactly at zero remains
break-even, and flat-zero intervals are never counted as profitable.

These are analytic integrals **conditional on the model**, not empirically
established frequencies. Expected P/L is not a typical outcome, guarantee,
available quote, or maximum-loss measure. Exclusions include jumps, changing
volatility, early exercise, assignment paths, margin, slippage, taxes,
discrete dividends, and financing/borrow cash flows. Daily-reset leveraged
ETFs are especially sensitive to path-dependent compounding; a fixed
lognormal terminal distribution is a fragile assumption for these products.

## Validation and references

Tests cover independent vanilla call/put moments and profit thresholds,
stock/put/call parity, long/short complements excluding flats, deterministic
limits, opening credits and fees, drift/volatility sensitivity, wide
distributions, normalization, measure validation, HTML escaping, and
independence from entered option IV/current marks.

```sh
uv run pytest tests/unit/test_distribution_lab.py
uv run ruff check .
uv run mypy src/options_analysis
```

The example report was visually checked at 1440px and 390px widths with no
page-level horizontal overflow; tables scroll inside their cards.

Primary references checked during implementation:

- [NIST: Lognormal distribution](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3669.htm)
  supplies the lognormal/normal CDF relationship and distribution moments.
- [SEC: Leveraged and inverse ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec)
  discusses reset periods, compounding and longer-holding-period risk.

Before considering a merge, evaluate whether conditional assumptions help
decisions more than they encourage false precision. No automatic ranking,
position suggestion, or order interface is included.
