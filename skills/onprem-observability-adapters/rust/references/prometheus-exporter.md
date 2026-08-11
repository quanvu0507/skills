# Prometheus-compatible exporter

## Branch on the environment first

```text
server/worker with central_scrape=true -> Prometheus-compatible exporter on an existing approved management path or port
desktop-local with central_scrape=false -> local diagnostics only; no background external exporter
```

Read `features.central_scrape` from the environment profile before deciding
anything else. The language does not determine whether an exporter is appropriate.

## Server and worker: exporter placement

Serve metrics from a path on the port the service already binds:

```rust
let app = Router::new()
    .route("/api/v1/...", /* business routes */)
    .route("/metrics", get(metrics_handler))
    .route("/health", get(live))
    .route("/ready", get(ready));
```

A worker with no inbound HTTP is the one case that needs its own listener. Bind it
to the internal interface the environment profile specifies, never `0.0.0.0`
without a stated reason, and register it as a scrape target the same way.

**Management paths must not be reachable from outside.** Run a negative probe from
outside the boundary before rollout and record the result — an ingress that
forwards `/` forwards `/metrics` too.

## The handler never blocks

```rust
async fn metrics_handler(State(state): State<AppState>) -> impl IntoResponse {
    // Encode from in-memory registry state only.
    let body = state.registry.encode_text();
    ([(header::CONTENT_TYPE, "text/plain; version=0.0.4")], body)
}
```

The handler must not query a database, call a dependency, take a contended lock or
perform file I/O. The scraper calls it every 15–30 seconds forever; work done here
is permanent background load and a denial-of-service surface. `unwrap()` here is
especially costly: a panic during an incident removes the metrics exactly when
they are needed.

If a value is expensive to compute, compute it on the owning task and publish it
through an `ArcSwap` or an `AtomicU64` that the handler reads.

## Labels are bounded enums or templates

```rust
#[derive(Clone, Copy)]
enum Outcome { Success, Failure, Timeout, Cancelled }

impl Outcome {
    fn as_label(self) -> &'static str {
        match self {
            Outcome::Success => "success",
            Outcome::Failure => "failure",
            Outcome::Timeout => "timeout",
            Outcome::Cancelled => "cancelled",
        }
    }
}
```

Returning `&'static str` from a closed enum makes an unbounded label a compile
error rather than a production incident.

**Never a label:**

```text
tokio task id or task name derived from data
user id, session id, device id, tenant id
request id, correlation id, trace id
raw path or URL — use the route template
error message or Debug output of an error type
channel contents or any payload value
```

Tokio task and channel metrics label by **kind** from a fixed set:

```rust
task_spawned_total{task_kind="ingest"}
channel_depth{channel="ingest_queue"}
```

`task_kind` and `channel` are compile-time constants, not runtime strings.

## Core metric set

| Metric | Type | Labels |
|---|---|---|
| `http_server_requests_total` | counter | `method`, `route`, `status_class`, `outcome` |
| `http_server_request_duration_seconds` | histogram | `method`, `route` |
| `worker_task_total` | counter | `task_kind`, `outcome` |
| `worker_task_duration_seconds` | histogram | `task_kind` |
| `worker_tasks_in_flight` | gauge | `task_kind` |
| `channel_depth` | gauge | `channel` |
| `channel_send_blocked_total` | counter | `channel` |
| `dependency_up` | gauge | `dependency` |

Compute the expected series count as the product of the label domains before
adding any of them, and record it in the metric inventory.

## Route normalization in Axum

Use `MatchedPath`, never `uri.path()`:

```rust
let route = req
    .extensions()
    .get::<MatchedPath>()
    .map(|p| p.as_str().to_owned())
    .unwrap_or_else(|| "other".to_owned());
```

Unmatched requests all collapse into `other`. Without this, any client — including
a scanner — controls your label domain.

## Version pinning

Pin the exporter crate to an exact version in `Cargo.toml` and record it in the
observability ADR. Exposition-format and registry APIs have changed across minor
versions of every Rust Prometheus crate.

## Tests

```text
the exporter output parses and contains exactly the expected metric names
label values come only from the closed enums
the handler performs no I/O — asserted by construction or by a timing bound
an unmatched route records "other", never the raw path
where central_scrape is false, no listener is created
expected series count matches the documented budget
```
