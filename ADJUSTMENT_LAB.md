# Hold / close / adjust comparison

This optional experiment lives on `eshen/adjustment-lab`. It compares an existing
position with closing today and up to eight explicit adjustments. It generates a
standalone HTML report and machine-readable JSON without a broker connection.
It does not recommend an action or assume a probability distribution.

Run from this branch after installing the repository's Python dependencies:

```sh
python -m options_analysis.experiments.adjustment_cli \
  examples/adjustment-comparison.json \
  --output-dir /tmp/adjustment-report
```

Open `/tmp/adjustment-report/report.html` in a browser. The report has a measure
selector for total P/L, change from today's value, and advantage versus Hold. It
also includes the explicit trade ledger, remaining positions, scenario tables,
and model checks. The report is self-contained and makes no network requests.
The companion `comparison.json` contains the same values and detailed curves.
Files in the chosen output directory are overwritten when the command is rerun.

The included `DEMO` example is fictional: a 100/120/140 call butterfly with
alternatives that roll one short call, or one short/long pair, upward. Its
deliberately arbitrary marks also show the model/mark mismatch warning. Replace
all prices, dates and IV assumptions before applying it to a real position.

## Input contract

`position` is the existing manual research request: one underlying, signed
original quantities, per-unit entry prices, optional current marks, option terms,
IV, rates, valuation date, `horizon_days`, `scenario_moves`, and `iv_shift`.
Option quantities are contract counts; stock quantities are shares. Positive
quantity is long and negative is short. All alternatives use the same horizon,
underlying prices, rates and absolute IV shift. The horizon must precede or equal
every original or traded option expiry; the lab rejects later dates instead of
silently comparing different dates. `scenario_days` and `risk_budget` are not
used by this single-horizon experiment.

Fees have separate, explicit roles:

- Set `position.fee_per_contract` and `position.fixed_fees` to zero. Those fields
  reserve round-trip fees in the main app and would conflict with this ledger.
- `entry_fees` are actual fees already paid for the original position.
- `close_fills` supplies one zero-based `leg_index`, assumed `fill_price`, and
  total `fees` for each original leg. Every leg needs one explicit fill. Current
  marks are never silently substituted for executable close prices.
- `hold_future_exit_fees` reserves future exit costs for Hold.
- Each named `adjustments` item has `trades` and optional `future_exit_fees`.
  Trade fees are the **total dollars for that trade**, not a per-contract rate.

An adjustment trade is a **change in quantity**, not the final position. Buying
one contract is `quantity: 1`; selling one is `quantity: -1`. It requires a
`fill_price` and its contract terms. Existing contracts inherit the original
effective IV, including opt-in calibration. New contracts require explicit
`implied_volatility`. If the same contract is bought and sold, it uses one common
IV, and net zero positions are removed. There is no automatic strike choice,
estimated fill, lot selection or transaction execution.

## Accounting

For signed quantity changes, multiplier `m`, and per-unit fills `p`:

```text
Gross trade cash      = -sum(quantity_change * m * p)
Net cash today        = gross trade cash - trade fees
Future wealth         = net cash today + future position value - future exit fees
Total P/L             = future wealth - original entry value - entry fees
Change from today     = future wealth - today's original position value
Advantage versus Hold = future wealth - Hold's future wealth
```

A short's original entry value is negative (a credit), and its current value is
negative (a liability). Opening credits and closing debits are counted exactly
once. The original basis is never reset to replacement premiums after a roll.
Close has no remaining position and therefore produces a flat future result.
Cash earns no interest; negative cash has no financing cost in this experiment.

Future option values use the core European model with exact intrinsic value at
expiry. Today's original value uses entered marks where supplied and model
prices otherwise. A zero-day model scenario can differ from today's entered
marks; the report preserves and discloses that difference. A larger return at
one scenario can accompany worse outcomes elsewhere.

The displayed ledger tracks economic receipts and payments, **not tax-lot
realized gains**. The lab excludes taxes, tax deferral, wash sales, early
assignment, margin, share dividends, borrow costs, and adjusted deliverables.
Its finite chart is not a maximum-loss guarantee. This is intentionally separate
from the main application's interface while the workflow is evaluated.

## Verification

```sh
pytest tests/experiments/test_adjustments.py
ruff check src/options_analysis/experiments tests/experiments
mypy src/options_analysis/experiments
```

Regressions cover hand-calculated partial rolls, short liabilities and credits,
fee reconciliation, explicit close fills, common-horizon validation, shared IV,
model/mark mismatch, and escaping of HTML, script, and template-like labels.
