# ADR: observability for <service>

**Status:** Proposed | Accepted | Superseded
**Date:** YYYY-MM-DD
**Deployment model:** onprem
**Environment profile:** <kubernetes-talos | docker-dokploy | vm-systemd | bare-metal>

## Context

<What the service does, which boundaries are active, and what question the
instrumentation must answer. Name the operational failure that motivated this —
"we could not tell whether the consumer was stuck" is a reason; "we should have
metrics" is not.>

## Decisions

### Registry

- Private `PrometheusRegistry` owned by the application; the default registry is
  not used.
- Prometheus Java client version: `<exact version>`
- JVM/process collectors registered: yes | no

### Exposition

- `/metrics` served from the existing Play port via `ManagementController`.
- No second HTTP server and no second container port.
- Management paths blocked at the gateway; negative probe recorded below.

### Route normalization

- Route template taken from `Router.Attrs.HandlerDef`.
- Unmatched requests recorded as `route="other"`.
- Route domain size: `<n>` (see the metric inventory).

### Health

- `live` = process and framework booted.
- `ready` = `<list the local components that must be initialized>`.
- Dependency degradation is reported through `dependency_up`, and does **not**
  fail readiness.

### Logging

- JSON Lines to stdout, encoder `<library@version>`.
- Terminal HTTP event: `http_request_completed`, emitted exactly once.
- Redacted at source: `<header and field list>`.
- Context propagation: `<explicit context | scoped mechanism>`; MDC is not relied
  on across future boundaries.

### Kafka (if applicable)

- `KafkaConsumer` remains single-threaded and is touched only by the poll loop.
- Metrics read an immutable snapshot published by the poll thread.
- Existing poll → persist → commit ordering is unchanged.
- Partition-labelled metrics: `<yes/no>`; partition count `<n>`.

### Scheduled jobs (if applicable)

- Outcomes: `success`, `partial_failure`, `failure`, `skipped_lock`.
- Recorded at the advisory-lock boundary, outside lock acquisition.
- `job_name` domain: `<fixed list>`.

## Explicit non-goals

```text
OpenTelemetry SDK / agent / OTLP exporter
Tempo or distributed tracing
a second HTTP server or port
generic auto-instrumentation
any change to the remote Akka protocol shape
any Grafana Cloud or SaaS telemetry destination
```

## Cardinality

- Total expected series: `<n>` (from `metric-inventory.template.yaml`)
- Series budget agreed with the platform owner: `<n>`
- Rejected labels and why: see the inventory

## Ownership

| Layer | Repository |
|---|---|
| application code | `<repo>` |
| deployment / scrape | `<repo>` |
| dashboards | `<repo>` |
| alert rules and routing | `<repo>` |

## Rollout and rollback

| Step | Evidence required |
|---|---|
| application deployed | image tag/digest and deploy revision |
| scrape configured | target `up` and expected series present |
| dashboard | built only after series exist |
| baseline | observed over `<period>` |
| alert rules | written only after baseline |
| alert delivery | synthetic alert observed by a human |

Rollback per layer: application `<how>`, scrape `<how>`, dashboard `<how>`,
rules `<how>`.

## Verification record

| Check | Evidence level | Source |
|---|---|---|
| `/metrics` responds on the existing port | | |
| `/metrics` refused from outside the boundary | | |
| expected series present after scrape | | |
| one JSON log line per request | | |
| no credential or payload in logs | | |
| Kafka ordering unchanged | | |
| one outcome per scheduled run | | |

Evidence levels: `source-confirmed`, `runtime-evidence`, `inference`,
`not-verified`.
