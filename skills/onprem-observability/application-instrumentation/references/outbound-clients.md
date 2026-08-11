# Database and outbound HTTP clients

Both are the same shape: a call leaves the process, and it succeeds, fails, times
out or is cancelled. Instrument them identically so one dashboard pattern covers
every dependency.

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `dependency_requests_total` | counter | `dependency`, `operation`, `outcome` |
| `dependency_request_duration_seconds` | histogram | `dependency`, `operation` |
| `dependency_requests_in_flight` | gauge | `dependency` |
| `dependency_up` | gauge | `dependency` |
| `connection_pool_size` | gauge | `pool` |
| `connection_pool_in_use` | gauge | `pool` |
| `connection_pool_wait_seconds` | histogram | `pool` |

`dependency` is a fixed logical name — `postgres`, `payments-api` — not a hostname
and not a URL. Hostnames change with environment and rotation, which starts a new
series each time and breaks every historical comparison.

## Operation labels are the trap

**Never label with the SQL text or the resolved URL.** Both are unbounded, and a
query built by string concatenation makes the label domain unbounded by
construction.

```text
query text                   ->  a fixed operation name: "load_device_by_id"
/api/orders/8f2c/items       ->  route template: "/api/orders/{id}/items"
```

Give each call site a stable operation name from a fixed list defined in code. If
the list is long enough to be annoying, that is the cardinality warning arriving
early rather than in production.

## Outcomes

```text
success
failure     the dependency answered with an error
timeout     the client's deadline elapsed
cancelled   the caller went away first
```

`timeout` and `cancelled` must stay distinct. Rising timeouts point at the
dependency; rising cancellations point at callers or shutdown. Collapsing both into
`failure` makes each undiagnosable.

## Connection pools

Pool exhaustion presents as "the application is slow" with every dependency metric
looking fine, because the time is spent waiting for a connection before the call
starts. `connection_pool_wait_seconds` is what distinguishes it — measure the wait
separately from the call.

## Dependency health, not readiness

Expose `dependency_up` and alert on it. Do **not** fail readiness when a dependency
is unhealthy: every replica would leave the load-balancer pool simultaneously
during a shared-dependency incident, turning degradation into a total outage.

## Retries

Count attempts and final outcomes separately:

```text
dependency_requests_total{outcome="failure"}   final outcome per logical call
dependency_attempts_total{outcome="failure"}   every attempt, including retried
```

Counting only attempts makes a healthy retry look like an outage; counting only
final outcomes hides a dependency that needs three attempts every time.

## Logs

Log a failed dependency call once, at the boundary that handled it, with a finite
`error_kind` and a bounded message. Never log the query parameters, the request
body or the credentials in the connection string.

## Tests

```text
one test per outcome, including timeout and cancellation
operation labels come from the fixed list; no SQL or URL reaches a label
in-flight returns to zero after a cancellation
pool wait time is recorded separately from call duration
a failed call logs exactly once, with no credential in the message
