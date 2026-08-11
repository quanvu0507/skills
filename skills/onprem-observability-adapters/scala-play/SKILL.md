---
name: scala-play
license: Apache-2.0
compatibility: "Scala 2.13, Play 2.8+, Akka, Prometheus Java client 1.x, Grafana OSS, Loki OSS, VictoriaMetrics; no Grafana Cloud dependency"
description: "Instrument Scala/Play/Akka services for on-premises Prometheus-compatible metrics and JSON logging without changing business behaviour. Covers a private CollectorRegistry, reusing the existing Play port and request lifecycle, normalized route labels, safe Kafka consumer metrics, advisory-lock scheduled-job outcomes, Logback JSON encoding and health-state semantics. Use when adding or reviewing metrics, logging or health endpoints in a Scala, Play or Akka service, or when a legacy Play service must expose /metrics to VictoriaMetrics."
---

# Scala/Play observability adapter

Implements [`observability-contract`](../../onprem-observability/observability-contract/SKILL.md)
for Scala/Play/Akka services. Read the contract first — this skill only adds
language and framework specifics.

## Non-goals

Do not introduce any of these as part of instrumentation work:

```text
OpenTelemetry SDK, agent or OTLP exporter
Tempo or distributed tracing
a second HTTP server or a second port
generic auto-instrumentation of every query or method
a change to the remote Akka protocol shape
```

Each one changes the deployment or wire contract. They are separate decisions with
their own plan and approval.

## Decision workflow

```text
private Prometheus registry
existing Play port
management controller
reuse request lifecycle
normalized route
single-thread KafkaConsumer access
immutable metrics snapshot
SingleFlight job boundary
JSON Logback encoder
health-state machine
```

Work through it in order; each step assumes the previous one.

1. **Private registry.** Create one `CollectorRegistry` owned by the application
   rather than using the global default. The global default is process-wide
   mutable state: two components registering the same collector throw at startup,
   and tests that run in the same JVM leak metrics into each other.
   → [`references/private-registry.md`](references/private-registry.md)

2. **Existing port and a management controller.** Serve `/metrics` from the
   routes file on the port Play already binds. A second server means a second
   container port, a second probe, a second Gateway rule and a new exposure
   surface. → [`references/http-and-health.md`](references/http-and-health.md)

3. **Reuse the request lifecycle.** Instrument in a Play filter or the existing
   error handler so the terminal event fires exactly once, including on failure.

4. **Normalized route.** Take the route template from Play's `HandlerDef`, never
   `request.uri`. → [`references/http-and-health.md`](references/http-and-health.md)

5. **Kafka consumer safety.** Metrics observe the existing control flow and never
   touch `KafkaConsumer` from a request thread.
   → [`references/kafka-consumer-metrics.md`](references/kafka-consumer-metrics.md)

6. **Scheduled jobs.** One terminal outcome per run, recorded at the lock
   boundary. → [`references/scheduled-jobs.md`](references/scheduled-jobs.md)

7. **JSON logging.** A Logback encoder that emits one JSON object per line with
   semantic fields. → [`references/json-logback.md`](references/json-logback.md)

8. **Health state machine.** `live` and `ready` mean different things and neither
   means "all dependencies are healthy".
   → [`references/http-and-health.md`](references/http-and-health.md)

## Scala-specific traps

| Trap | Why it breaks | Do instead |
|---|---|---|
| recording in `Future.onComplete` without covering `Failure` | error rate reads zero during an outage | record in a single combinator that sees both outcomes |
| `MDC` across `Future` boundaries | the execution context swaps threads, so fields attach to the wrong request | pass context explicitly or bind it to the unit of work |
| a `var` holding the current correlation ID | concurrent requests overwrite each other under load only | carry it in the request context |
| labelling by actor path | one series per actor instance | label by actor type from a fixed set |
| `Await.result` inside a metrics handler | a scrape timeout stalls a request thread | read a precomputed immutable snapshot |
| exception message as a label | unbounded label domain | classify into a finite `error_kind` |

## Assets

- [`assets/metric-inventory.template.yaml`](assets/metric-inventory.template.yaml) —
  fill one row per metric before writing code; the series-count column is what
  catches an unbounded label before it reaches production.
- [`assets/observability-adr.template.md`](assets/observability-adr.template.md) —
  record registry, port, route-normalization and health decisions once, so the
  next change does not relitigate them.

## Verification

```text
sbt test passes, including a test per terminal outcome
/metrics responds on the existing port and is not reachable through the public gateway
a scrape of a running instance returns the expected series and no unexpected ones
one JSON log line per request, valid JSON, terminal event exactly once
Kafka poll -> persist -> commit ordering is byte-for-byte unchanged
each scheduled job emits exactly one outcome per run, including the skipped-lock case
```
