# Correlation and security

## Correlation lives in log fields

A request ID and a correlation ID are unbounded by construction: one value per
request. They belong in the JSON log line as fields, and nowhere else.

```text
request_id      identifies this hop
correlation_id  identifies the end-to-end flow across services
```

Propagate the correlation ID on outbound calls through a header, and log it on
both sides. Correlation then works by querying logs:

```logql
{namespace="apps", app="example-service"} | json | correlation_id="01J..."
```

**Never** promote either identifier to:

- a Prometheus/VictoriaMetrics metric label — one series per request;
- a Loki index label — one stream per request, which degrades ingestion and query
  for every tenant sharing the instance, not just this service.

Loki parses JSON fields at query time. That is the intended mechanism for
high-cardinality lookup, and it costs nothing at write time.

## Context propagation across concurrency

Correlation context must travel with the unit of work, not in a process-global
mutable slot. A single mutable holder shared across concurrent futures, tasks or
threads produces mislabeled logs under load — the failure appears only when
traffic is high, which is when the logs matter most, and it looks like a data bug
rather than an instrumentation bug.

```text
carry the context explicitly through the call chain, or
use the runtime's task-local / scoped mechanism bound to the unit of work
never a mutable global, a thread-local reused across a pool, or a singleton holder
```

When a request spawns background work that outlives the response, copy the
correlation ID into that work explicitly. Do not assume inherited context.

## Sensitive data

Redact at the point of construction, before the value reaches an encoder or an
exporter:

```text
credentials, tokens, API keys, Authorization headers, cookies
signed URLs and signed query strings
request and response bodies
decoded authentication data and JWT claims
personal data beyond the project's data classification
```

Filtering later — in the collector or in a Loki pipeline stage — is not redaction.
The value was already written to the node's disk and may already be in a backup.

## Identity in labels

Metric labels must not carry identity, even when the identity looks small today.
"We only have 50 devices" becomes 50,000 after a rollout, and the series are
already written. Model identity as:

```text
a log field, queried on demand, or
a bounded classification: device_type, region, tier — enumerable before deploy
```

If a per-entity view is genuinely required, it is a logs or a database question,
not a metrics question.

## Secret scanning

Before publishing an artifact, a library version or a configuration file:

```text
scan the diff for credential patterns, private keys and cloud tokens
confirm no environment file, keystore or dotenv is included
confirm example configuration uses placeholders, not real endpoints
confirm generated config contains no SaaS domain or publisher role
```

A published artifact version is immutable in practice: consumers cache it. A leak
requires rotation of the secret, not just a new version.
