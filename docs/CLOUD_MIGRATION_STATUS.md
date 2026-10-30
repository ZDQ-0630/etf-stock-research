# Cloud migration: incomplete, test branch only

This branch carries the existing published Oct 29 model-monitor output and stock-data snapshot as dated reference material; they are not current market data. Core algorithms match the October 29 public website by SHA-256. The new `tools/cloud_calculate.mjs` only recalculates existing public stock scenarios using supplied prices. It records input/core/calculator hashes and explicitly blocks unimplemented parts. It does not download data, evaluate fresh earnings, update ETF history, calculate ETF costs and FX, or publish a website. Its result is not a buy signal.

Run from the repository root with Node 20.11 or newer:

```
node tools/cloud_calculate_test.mjs
node tools/cloud_calculate.mjs <input.json> <new-output.json>
```

Inputs require `run_id`, `baseline_stocks.companies` and two `quotes.observations` per symbol. Each observation must include symbol, official_regular_close session, trade_date, UTC close timestamp, retrieval timestamp, price, provider_id, HTTPS source_url and SHA-256 of the original source response. `calendar` must contain source_url `https://www.nyse.com/trade/hours-calendars`, source_sha256, checked_at and unplanned_closure_reviewed=true. The latter is an explicit external attestation, not independently verified by this program. The guard checks the 2026 exchange schedule, America/New_York time zone, latest completed session, 2026 early closes, freshness and consistency between two distinct provider IDs and hostnames. A 0.1% or one-cent tolerance is an illustrative quality threshold, not a claim of accuracy. Provider ownership, source content, exchange-specific closes, hash-to-raw matching and unscheduled closures still require independent verification. Date-only daily bars cannot satisfy the timestamp requirement without a correctly documented upstream adapter. Outside 2026 all quotes are blocked until the calendar is reviewed and updated. The old `quotes.raw` input is blocked. Previous comparison prices and scenarios remain as supplied and are not independently verified.

These fields are necessary, not sufficient proof: syntactically valid hashes, domains and asserted labels can be fabricated. Source acquisition and content review remain unimplemented, so this code cannot itself produce verified quotes. Output paths must not already exist. Do not publish raw vendor records without checking redistribution rights. Do not publish private account information.

Further work before a cloud schedule: obtain authorized and verifiable sources; implement each blocked module; establish persistent versioned state; compare independently sourced data; verify unattended access and same-Site publication; run the full pipeline and read results back. No workflow, schedule, current investment result or live website update is claimed here.
