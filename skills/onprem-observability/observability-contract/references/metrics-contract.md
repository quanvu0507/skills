# Metrics contract

## Naming, unit and type

```text
<namespace>_<subsystem>_<name>_<unit>
```

- `_total` suffix for counters, `_seconds` for durations, `_bytes` for sizes;
- base units only — seconds, not milliseconds; bytes, not kilobytes;
- the name describes what is measured, never who measured it;
- a metric name is a public API. Renaming one silently breaks every dashboard,
  rule and recording rule that used it, so rename through a deprecation window
  with both names emitted.

| Type | Use for | Never use for |
|---|---|---|
| counter | monotonically increasing totals | values that can decrease |
| gauge | a current value that moves in both directions | totals |
| histogram | latency and size distributions | high-cardinality identity |
| summary | avoid — quantiles cannot be aggregated across instances | anything aggregatable |

## Exact-once terminal recording

A request, job or message increments its outcome counter **exactly once**, at the
terminal boundary, on every path including failure and cancellation. Two common
bugs:

- recording on the success path only, so the error rate reads zero during an
  outage — the metric looks healthiest exactly when the service is worst;
- recording in both a wrapper and the handler, so rates are doubled and no
  dashboard agrees with the logs.

Success and failure share one counter with an `outcome` label rather than living
in two separate counters; that makes ratios a single query and keeps them
consistent.

## Finite labels

Every label value must come from a set you can enumerate before deployment.

**Allowed:** `outcome` (`success`/`failure`/`timeout`), `method`
(`GET`/`POST`/…), normalized `route`, `status_class` (`2xx`/`4xx`/`5xx`),
`job_name` from a fixed list, `dependency` from a fixed list.

**Forbidden:**

```text
raw URI or URL
request ID, correlation ID, trace ID
device serial, camera serial, fleet ID, tenant ID, user ID
actor path or thread name
exception message or stack frame
raw Kafka topic, partition or offset
any payload value
free-text error strings
```

Each forbidden value multiplies the series count without bound. One unbounded
label on one metric can produce more series than the rest of the service combined
and takes down queries for every other team using the same VictoriaMetrics.

**Series budget:** state the expected series count for each metric before adding
it — the product of every label's domain size. If you cannot compute the product
because a domain is unknown, that domain is not finite and must not be a label.

## Route normalization

Instrument the route **template**, not the resolved path:

```text
/api/v1/devices/8f2c-…/telemetry   ->   /api/v1/devices/{id}/telemetry
```

Take the template from the router when the framework exposes it. When it does not,
maintain an explicit ordered list of patterns and map unmatched paths to a single
`other` bucket — never to the raw path. An unmatched-path counter tells you when
the list needs updating.

## Readiness versus dependency health

```text
live  = the process and framework started
ready = local essential components are initialized and running
dependency degradation = metrics, logs and alerts — not an automatic readiness failure
```

Making readiness fail when a downstream dependency is unhealthy causes the
orchestrator to remove every replica during a shared-dependency incident,
converting a partial outage into a total one. Expose dependency health as its own
gauge and alert on it; keep readiness about this instance.

## Histograms

Buckets are chosen from the observed distribution, not from habit. Review them:

- when the p99 lands in the top or bottom bucket, the distribution is not being
  measured — resolution is lost exactly where it matters;
- bucket count multiplies series count; keep it modest and justified;
- changing buckets changes historical comparability, so record when they changed.

## Definition of done for a metric

```text
name, unit and type documented
label set enumerated with each domain's size
expected series count computed and bounded
recorded exactly once at the terminal boundary, on every path
emitted by a running instance and confirmed present after scrape
a consumer exists: a dashboard panel or a rule
tests cover every terminal outcome including cancellation and cleanup
```
