---
name: rust
license: Apache-2.0
compatibility: "Rust 2021/2024, tracing, Tokio, Axum, Prometheus-compatible exporters, Grafana OSS, Loki OSS, VictoriaMetrics; no Grafana Cloud or OTLP requirement"
description: "Instrument Rust services, workers and desktop applications for on-premises observability. Covers structured JSON logging with tracing, Prometheus-compatible exporters gated on the environment profile, Tokio task and channel boundaries, cancellation and timeout outcomes, and desktop-local diagnostics without a background exporter. Use when adding or reviewing logging, metrics or health signals in a Rust service, a Tokio worker, an Axum API or a Rust desktop application."
---

# Rust observability adapter

Implements [`observability-contract`](../../onprem-observability/observability-contract/SKILL.md)
for Rust. Read the contract first — this skill only adds language specifics.

Rust runs in more shapes than the other adapters: a server behind a scrape, a
worker with no inbound traffic, and a desktop application on a machine the
platform does not manage. **The environment profile, not the language, decides
what telemetry is possible.**

## Non-goals

```text
OpenTelemetry SDK or OTLP export (opt-in per project, never a default)
Tempo or distributed tracing
a second management server on a desktop application
a background exporter that phones home from a user's machine
central scrape for desktop-local projects unless the profile enables it
```

## Environment branching

| Environment | Metrics | Logs | Runtime skill |
|---|---|---|---|
| `kubernetes-talos` | exporter, scraped | stdout → Alloy → Loki | `kubernetes-observability` |
| `vm-systemd` / `bare-metal` | exporter, `vmagent` static/file discovery | stdout or journal → Alloy | `vm-docker-observability` |
| `docker-dokploy` | exporter, Docker/host discovery | stdout → Alloy | `vm-docker-observability` |
| `desktop-local` | **local diagnostics only** | local rotating file | none by default |

`central_scrape: false` means no exporter listening in the background. A desktop
application that opens a metrics port is an unrequested listening socket on
someone's workstation and a data-egress question — not an implementation detail.
→ [`references/desktop-local.md`](references/desktop-local.md)

## Decision sequence

```text
1. Read the environment profile: central_scrape, telemetry_egress, logs backend.
2. Read the project profile: declared capabilities and logging/metrics state.
3. Structured logging first — it works in every environment.
4. Add an exporter only when central_scrape is true.
5. Define terminal outcomes for every async boundary before writing code.
6. Prove every label domain is finite.
7. Test cancellation, timeout and cleanup paths, not just the happy path.
```

## References

| Topic | Reference |
|---|---|
| JSON logging with `tracing` | [`structured-logging.md`](references/structured-logging.md) |
| exporter choice and label rules | [`prometheus-exporter.md`](references/prometheus-exporter.md) |
| tasks, cancellation, channels | [`tokio-boundaries.md`](references/tokio-boundaries.md) |
| desktop applications | [`desktop-local.md`](references/desktop-local.md) |

## Rust-specific traps

| Trap | Why it breaks | Do instead |
|---|---|---|
| recording after `.await` in a dropped future | a cancelled task records nothing; in-flight gauges leak upward forever | record in a `Drop` guard so cancellation is still terminal |
| `tracing::info!("{}", err)` for errors | the message is unstable and unqueryable | emit a stable event name plus fields |
| task id or `tokio::task::Id` as a label | unbounded label domain | label by task **kind** from a fixed set |
| `unwrap()` in an exporter handler | a scrape panics the task and metrics vanish during an incident | return an error and record it |
| a `String` error rendered into a label | unbounded free text | map to a finite `error_kind` |
| blocking I/O inside an async metrics handler | stalls the executor for every task on that thread | precompute; serve from memory |
| unbounded channel with no depth metric | memory grows silently until OOM | bounded channel plus a depth gauge |

## Verification

```text
cargo test passes, with a test per terminal outcome including cancellation
cargo clippy is clean on the instrumentation modules
a captured log line parses as valid JSON with the expected fields
where central_scrape is true: the exporter endpoint returns the expected series
where central_scrape is false: no listening socket is opened for telemetry
in-flight gauges return to zero after a cancellation storm
channel depth gauges are present for every bounded channel
```
