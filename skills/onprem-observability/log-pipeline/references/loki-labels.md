# Loki labels

## Streams, and why the count matters

A Loki stream is one unique combination of index label values. Loki keeps state per
stream, so stream count — not log volume — is the thing that breaks an instance.

```text
{namespace="apps", app="example", pod="example-7d9f-2xk4", level="INFO"}
```

Four labels, and the stream count is the product of their cardinalities. Adding
`request_id` to that set means one stream per request: ingestion slows, the index
grows without bound, and queries degrade for every tenant sharing the instance.

## Allowed as index labels

```text
namespace, app, service, component
pod, container, host, node
job, instance
level, stream (stdout/stderr)
environment, tier, region
```

All are bounded by the platform, change rarely, and are the things people actually
filter on first.

## Never index labels

```text
request_id, correlation_id, trace_id, span_id
user_id, device_id, session_id, tenant_id
route, path, url, query
status code, error message, exception type
timestamp or any value derived from time
any value taken from the log message body
```

`level` is the borderline case that is fine: five values, and filtering by level is
the most common first query.

## Where high-cardinality values go

Parse them at query time. Loki is designed for this; it costs nothing at write.

```logql
{namespace="apps", app="example-service"}
  | json
  | correlation_id="01J8ZQ..."
```

```logql
{namespace="apps", app="example-service"}
  | json
  | duration_ms > 1000
  | route="/api/v1/devices/{id}"
```

The stream selector stays bounded; the filtering happens on the returned lines.

## Structured metadata

Newer Loki versions support attaching key-value metadata to a line without creating
a stream. It suits values queried often but too numerous to index — a trace id, for
example. **Confirm the deployed Loki version supports it** before designing around
it; on an older version the configuration is accepted in some paths and ignored in
others.

## Pod and container labels

`pod` is bounded by replica count but churns on every rollout, creating new streams
each deploy. That is acceptable and normal — do not try to remove it, since it is
how you find one bad replica. What is not acceptable is a label that churns per
request.

## Deriving labels in Alloy

Deriving a label from the log body is where unbounded labels get introduced by
accident:

```text
do not promote a parsed JSON field to a label because it is convenient
do not extract a status code, a route or an id into a label
do promote a bounded value that is genuinely missing from the metadata, e.g. level
```

Every promotion needs its cardinality stated before it is added.

## Diagnosing a label mistake

```logql
# How many streams does this selector match?
count(count_over_time({namespace="apps", app="example-service"}[1h]) by (__stream__))
```

A stream count that grows linearly with traffic means an unbounded label is in the
set. Fix it at the source; existing streams remain until retention removes them.

## Checklist

```text
index labels enumerated with each cardinality
stream count computed and stated
no identifier, route, status or message-derived value is a label
high-cardinality queries demonstrated with query-time parsing
structured metadata used only if the deployed version supports it
