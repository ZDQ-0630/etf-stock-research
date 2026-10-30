# Cloud migration: incomplete, test branch only

This branch carries the existing published Oct 29 model-monitor output and stock-data snapshot as dated reference material; they are not current market data. Core algorithms match the October 29 public website by SHA-256. The new `tools/cloud_calculate.mjs` only recalculates existing public stock scenarios using supplied prices. It records input/core/calculator hashes and explicitly blocks unimplemented parts. It does not download data, evaluate fresh earnings, update ETF history, calculate ETF costs and FX, or publish a website. Its result is not a buy signal.

Run from the repository root with Node 20.11 or newer:

```
node tools/cloud_calculate_test.mjs
node tools/cloud_calculate.mjs <input.json> <new-output.json>
```

Inputs require `run_id`, `quotes.retrieved_at`, `quotes.raw` (Longbridge-style symbols, timestamp and regular close), and `baseline_stocks.companies` (dated previous price and explicitly stated scenario EPS, PE and years). Output paths must not already exist. Do not publish raw vendor records without checking redistribution rights. Do not publish private account information.

Further work before a cloud schedule: obtain authorized and verifiable sources; implement each blocked module; establish persistent versioned state; compare independently sourced data; verify unattended access and same-Site publication; run the full pipeline and read results back. No workflow, schedule, current investment result or live website update is claimed here.
