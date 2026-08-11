# Severity model

```text
P0 = active security/data-loss emergency
P1 = production blocker or severe operational blind spot
P2 = important correctness/operability gap
P3 = improvement/design consistency
```

## Severity = impact × evidence

Both are required. A severe theoretical impact with `not-verified` evidence is not
P0 — it is a P2 or P3 with an explicit note that verification would change the
rating. Promoting on speculation inflates the whole report and trains readers to
discount it.

| Evidence | Highest severity available |
|---|---|
| `runtime-reproduced` | P0 |
| `runtime-evidence-supplied` | P1 |
| `source-confirmed` | P1 |
| `inference` | P2 |
| `not-verified` | P3 |

A `source-confirmed` finding can reach P1 when the source alone is conclusive — a
credential written to a log line is conclusive from the code. It cannot reach P0
without confirmation that the affected path actually runs.

## P0 — active emergency

```text
a credential, token or personal data is being written to logs right now
telemetry is leaving the on-prem network to a SaaS destination
an unauthenticated management endpoint is reachable from outside
a change is actively losing or corrupting data
```

P0 means stop and fix now. Requires reproduced evidence that the condition is live.

## P1 — production blocker or severe blind spot

```text
an unbounded metric label that will exhaust the metrics backend
error rate recorded on the success path only, so outages read as healthy
readiness tied to downstream dependency health, turning partial into total outage
alerting declared complete while the rule engine or receiver is absent
ServiceMonitor/PrometheusRule in a VictoriaMetrics cluster: applies, reconciles nothing
a Kafka or ordering change made in the name of instrumentation
```

P1 blocks the release. These share a shape: the system appears instrumented and is
not, so no one is watching manually either.

## P2 — important gap

```text
missing terminal outcome for one path, such as cancellation
histogram buckets that put p99 in the top bucket
a dashboard panel that renders empty because it was written before the series existed
no runbook link on an alert
rollback documented for some layers but not all
log level misuse that trains operators to ignore errors
```

## P3 — improvement

```text
naming inconsistency across metrics
a panel that answers no operational question
a reference or comment that has gone stale
duplication between two skills or documents
```

## Two things severity must never do

**Never promote on speculation.** "This could be a security issue if the endpoint
were exposed" is P3 until exposure is checked. Check it, then rate it.

**Never recommend removing a unique Prometheus label without evidence.** A label
that looks redundant may be the only thing separating two series; removing it
merges them, and the resulting data is wrong rather than absent — a far worse
failure. Require the series-count query first:

```promql
count by (<label>) (<metric>)
```

## Ordering

Order findings by severity, and within a severity by evidence strength — reproduced
before supplied before source before inference. That puts the items a reader can
act on immediately at the top.

## Disagreement

When the author disputes a severity, record both positions and the evidence each
rests on. A dispute backed by a runtime query outranks a finding backed by
inference; a dispute backed only by assertion does not change the rating.
