# Logging contract

## Format

**JSON Lines to stdout.** One JSON object per line, no pretty-printing, no
multi-line values. The container or host runtime captures stdout; Alloy reads it
and writes to Loki. An application never writes directly to Loki and never opens a
network connection to a log backend.

```json
{"ts":"2026-08-11T09:12:33.481Z","level":"INFO","logger":"http","event":"http_request_completed","method":"GET","route":"/api/v1/devices/{id}","status":200,"duration_ms":42,"request_id":"01J...","correlation_id":"01J..."}
```

Rules:

- timestamps are RFC 3339 with milliseconds, in UTC;
- `level` is one of `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`;
- `event` is a stable snake_case identifier, not a sentence — sentences change,
  and every dashboard query that matched the old wording breaks silently;
- unknown-length values are bounded before they are written.

## One terminal HTTP event

Each request produces exactly one terminal log event, emitted where the response
is finalized, including on the error path. Not zero (silent failures), not two
(double-counted request rates that disagree with the metric).

The terminal event carries: method, normalized route template, status, duration,
request/correlation identifiers, and outcome classification. Intermediate
`DEBUG` events are allowed but never substitute for the terminal event.

## Semantic fields versus infrastructure labels

| Kind | Where it lives | Example |
|---|---|---|
| semantic field | inside the JSON line | `device_id`, `request_id`, `route`, `duration_ms` |
| infrastructure label | added by Alloy from the runtime | `namespace`, `app`, `pod`, `container`, `host` |

Infrastructure labels are bounded by the platform and are safe as Loki index
labels. Semantic fields are unbounded and are parsed at query time. Promoting a
semantic field to a Loki label multiplies the stream count by its cardinality and
degrades the whole tenant, not just that one query.

## Never logged

```text
request or response bodies
Authorization headers, cookies, session tokens, API keys
signed URLs and signed query strings
raw provider or third-party payloads
decoded authentication data, JWT claims, credentials of any kind
personal data beyond what the project's data classification allows
```

If a field might contain any of the above, redact at the source rather than
filtering downstream — a filter that runs in Alloy still means the secret was
written to disk on the node.

Redaction is explicit and testable:

```text
value is replaced with a fixed marker, not truncated
the marker is distinguishable from a legitimately empty value
a unit test asserts the sensitive value never reaches the encoder
```

## Throwables

Log the exception type, the message and a bounded stack trace on the terminal
event that failed. Do not:

- log the same throwable at multiple layers as it propagates — one failure becomes
  five error events and every error-rate panel is wrong;
- put the exception message into a metric label;
- swallow the throwable and log only a generic string, which makes the failure
  unattributable.

## Levels

| Level | Meaning |
|---|---|
| `ERROR` | the operation failed and a human needs to know |
| `WARN` | degraded but handled; retry succeeded, fallback used |
| `INFO` | terminal business or request events |
| `DEBUG` | developer detail, off in production by default |

An `ERROR` that fires on an expected condition (a client sending a malformed
request, an optional dependency being absent) trains operators to ignore errors.
Classify those as `WARN` or `INFO` with an outcome field.

## Verification

Before calling logging complete:

```text
a real log line is captured from the running service and parsed as valid JSON
the terminal event appears exactly once per request, including on failures
no forbidden field appears in a sample of at least one full request cycle
Alloy shows the stream arriving in Loki, and a LogQL query returns it
retention and ownership for the stream are written down
```
