# Structured logging in Rust

## One-line JSON with `tracing`

```rust
use tracing_subscriber::{fmt, EnvFilter};

fn init_logging() {
    fmt()
        .json()
        .flatten_event(true)          // fields at the top level, not nested under "fields"
        .with_current_span(false)     // avoid duplicating span data on every event
        .with_span_list(false)
        .with_timer(fmt::time::UtcTime::rfc_3339())
        .with_env_filter(EnvFilter::from_default_env().add_directive("info".parse().unwrap()))
        .init();
}
```

Pin `tracing`, `tracing-subscriber` and any encoder to exact versions in
`Cargo.toml`. The JSON field layout has changed between minor versions; a floating
version silently breaks every LogQL query that parsed the old shape.

`tracing` is used here as a structured logging facade. **It does not require an
OTLP exporter**, and none is configured unless the project profile explicitly
enables tracing.

## Stable event names, separate fields

```rust
// Yes — the event name is stable, the values are queryable fields.
tracing::info!(
    event = "http_request_completed",
    method = %method,
    route = %route_template,
    status = status.as_u16(),
    duration_ms = elapsed.as_millis() as u64,
    request_id = %request_id,
    "request completed"
);

// No — everything is trapped in a sentence that changes with the next reword.
tracing::info!("Request {} {} finished with {} in {:?}", method, uri, status, elapsed);
```

Use `%` (Display) or `?` (Debug) deliberately. `?` on a large struct emits the
whole structure into the log line, which is how payloads leak by accident.

## Bounded strings

Every string field that comes from outside the process is bounded before it is
logged:

```rust
fn bounded(value: &str, max: usize) -> Cow<'_, str> {
    if value.len() <= max { Cow::Borrowed(value) }
    else { Cow::Owned(format!("{}…[truncated]", &value[..floor_char_boundary(value, max)])) }
}
```

An unbounded field can exceed Loki's per-line limit, and then the **entire event
is dropped** — the error you most wanted is the one that disappears. Slice on a
character boundary; slicing a UTF-8 string at an arbitrary byte index panics.

## Explicit redaction

```rust
const REDACTED: &str = "[REDACTED]";

#[derive(Clone)]
pub struct Secret(String);

impl fmt::Debug for Secret {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str(REDACTED) }
}
impl fmt::Display for Secret {
    fmt_redacted!();
}
```

Wrapping secrets in a newtype whose `Debug` and `Display` both redact makes the
safe path the default: `?token` cannot leak, even in code written later by someone
who has not read this document. Filtering in the collector is not redaction — the
value already reached the node's disk.

Never logged: request or response bodies, `Authorization` headers, cookies, signed
URLs, API keys, decoded token claims, raw third-party payloads.

## Context across `.await`

Context travels with the future, not in a global:

```text
pass the context explicitly, or
use a tracing span entered for the scope of the work
never a static mut, a lazy_static Mutex holding "current request", or thread-local
  state reused across a work-stealing runtime
```

Tokio's work-stealing scheduler moves tasks between threads, so any thread-local
"current request" is wrong the moment there is concurrency — and it is wrong
silently, producing mislabeled logs only under load.

For spawned work that outlives its parent, clone the context into the spawn
explicitly:

```rust
let ctx = correlation.clone();
tokio::spawn(async move {
    let _span = tracing::info_span!("background_work", correlation_id = %ctx).entered();
    // ...
});
```

## Errors

Emit one event at the boundary that handled the error, with a stable event name, a
finite `error_kind` and the message as a **field** (never as a label on a metric):

```rust
tracing::warn!(
    event = "dependency_call_failed",
    dependency = "postgres",
    error_kind = %classify(&err),   // finite set: timeout | refused | protocol | other
    error = %bounded(&err.to_string(), 512),
    "dependency call failed"
);
```

Do not log the same error again as it propagates up the call stack; one failure
becoming five error events makes every error-rate panel wrong.

## Destination by environment

| Environment | Destination |
|---|---|
| container | stdout, collected by Alloy |
| `vm-systemd` | stdout to journal, or a file read by Alloy |
| `desktop-local` | local rotating file with a size cap; no network destination |

The application never opens a connection to Loki itself.

## Tests

```text
a captured line parses as valid JSON and contains the expected field names
the terminal event appears exactly once per request, including on the error path
a Secret value renders as the redaction marker under both Debug and Display
an oversized field is truncated on a character boundary and stays within the limit
concurrent tasks do not interleave correlation ids
```
