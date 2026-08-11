# HTTP API boundary

## One terminal record per request

Record where the response is finalized — a filter, middleware or the error handler
— so the same code path sees success and failure. Recording only where the handler
returns normally means the error rate reads zero during an outage: the metric looks
healthiest exactly when the service is worst.

If a framework short-circuits before your middleware (a routing failure, a body
that fails to parse, a panic handler), instrument that path too, and assert in a
test that a failing request produces exactly one record — not zero, not two.

## Metrics

| Metric | Type | Labels |
|---|---|---|
| `http_server_requests_total` | counter | `method`, `route`, `status_class`, `outcome` |
| `http_server_request_duration_seconds` | histogram | `method`, `route` |
| `http_server_requests_in_flight` | gauge | `route` |
| `http_server_request_size_bytes` | histogram | `route` (only if payload size matters) |

`status_class` (`2xx`/`3xx`/`4xx`/`5xx`) rather than the exact status keeps the
domain at four values. Keep the exact status in the log line, where it is free.

## Route normalization

Label with the **route template**, never the resolved path:

```text
/api/v1/devices/8f2c-4a/telemetry   ->   /api/v1/devices/{id}/telemetry
```

Take the template from the router. Where the framework does not expose one, keep an
explicit ordered pattern list and map everything unmatched to a single `other`
bucket. Count `other`: a rising rate means either a missing route or a scanner.

Without normalization the label domain is controlled by whoever sends requests,
including anyone probing random URLs from the internet.

## Outcome versus status

`status_class` describes what the client saw. `outcome` describes what the server
did. They differ in the cases that matter:

```text
a 404 for a legitimately absent resource   -> status 4xx, outcome success
a 200 with a partial result after a timeout -> status 2xx, outcome partial
a client disconnect before the response     -> outcome cancelled
```

Deriving outcome from status alone hides all three.

## In-flight

Increment at entry, decrement in a construct that runs on every exit path,
including panic, cancellation and client disconnect. An unpaired decrement makes
the gauge grow without bound.

## Latency

Measure from the first byte of the request being handled to the terminal outcome,
covering the failure path. Latency recorded only on success hides the slow failures
that usually cause the incident.

Choose histogram buckets from the observed distribution and review them when the
p99 lands in the top or bottom bucket — resolution is lost exactly where it
matters.

## Logs

One terminal JSON event per request, with method, route template, status, duration
and the correlation identifiers. No body, no `Authorization`, no cookies, no signed
query string. See the logging contract.

## Health endpoints

`/health` and `/ready` are not business routes. Exclude them from request metrics
or they dominate the rate — a probe every few seconds outnumbers real traffic on a
quiet service and makes every panel meaningless.

## Tests

```text
2xx, 4xx, 5xx and thrown-exception paths each record exactly one terminal event
an unmatched path records route="other", never the raw path
a client disconnect records a terminal outcome and releases in-flight
health probes do not appear in request metrics
label values come only from the declared finite domains
