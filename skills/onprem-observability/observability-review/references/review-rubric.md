# Review rubric

Work through every section. Record an evidence level per line, not a tick.

## 1. Baseline

```text
[ ] repository, branch and exact revision resolved and recorded
[ ] the requirements baseline (plan, design, issue) identified
[ ] scope stated: what was reviewed and what was not
[ ] the deployment model is onprem; no cloud or SaaS assumption anywhere
```

## 2. Metrics

```text
[ ] every metric has a name, unit, type and documented label domain
[ ] every label domain is finite and its size is stated
[ ] expected series count is computed and within the stated budget
[ ] terminal outcomes recorded exactly once, on every path including failure,
    timeout and cancellation
[ ] route labels use a normalized template; unmatched requests fall into one bucket
[ ] no identifier, payload, exception message or free text appears as a label
[ ] histogram buckets are justified; p99 does not sit in the top or bottom bucket
[ ] the metrics endpoint performs no I/O and cannot block
```

## 3. Logs

```text
[ ] JSON Lines to stdout, one object per line
[ ] exactly one terminal event per request, including on the error path
[ ] event names are stable identifiers, not sentences
[ ] no body, header, cookie, token, signed URL or decoded claim is logged
[ ] redaction happens at the source, with a fixed marker
[ ] throwables are logged once, at the handling boundary
[ ] high-cardinality values are fields, never Loki index labels
[ ] context propagation survives concurrency without a mutable global
[ ] log levels reflect whether a human must act
```

## 4. Collection

```text
[ ] the correct resource type for the environment
    (VMServiceScrape on kubernetes-talos; vmagent discovery elsewhere)
[ ] no ServiceMonitor, PodMonitor, PrometheusRule or serviceMonitor.enabled in a
    VictoriaMetrics profile
[ ] the target is confirmed up with a recent successful scrape
[ ] scrape timeout is below the interval, with margin
[ ] relabeling introduces no identity label
[ ] the log path is confirmed end to end: stdout -> Alloy -> Loki -> query
```

## 5. Health and availability

```text
[ ] live and ready are distinct and correctly scoped
[ ] readiness does not fail on downstream dependency health
[ ] liveness performs no dependency calls
[ ] dependency health is exposed as its own signal
[ ] probe timings are justified by measured response time
```

## 6. Exposure

```text
[ ] management paths enumerated
[ ] an explicit deny exists at the gateway or ingress
[ ] a negative probe from outside confirms refusal; output recorded
[ ] internal reachability confirmed for the scraper
```

## 7. Dashboards

```text
[ ] built after runtime series existed; queries were run and returned data
[ ] source JSON is authoritative and lives in the owning repository
[ ] source and generated artifact change in the same commit
[ ] ratios aggregate before dividing; instance identity aggregated away
[ ] the intentional empty state is distinguishable from a broken panel
[ ] logs links carry the time range and use bounded stream selectors
[ ] no template variable enumerates a high-cardinality label
```

## 8. Alerting

```text
[ ] baseline data exists and is recorded
[ ] the rule engine is enabled and evaluating
[ ] Alertmanager is enabled
[ ] a receiver is configured and owned by a named team
[ ] the rule was tested against sample data
[ ] a synthetic alert was delivered and observed by a human
[ ] every alert links to a runbook
[ ] for: is set; ratios guard against no-traffic NaN
```

If any line above is unmet, alerting is **not** operational. Say that plainly
rather than describing it as configured.

## 9. Ownership and rollout

```text
[ ] each layer's owning repository is named: app, deploy/scrape, dashboard, rules
[ ] the change sequence respects those boundaries
[ ] rollback is written per layer
[ ] a single-replica rollout is called out as an outage with a maintenance window
[ ] immutable image tag or digest is used
```

## 10. Behaviour preservation

```text
[ ] business ordering, threading and wire compatibility are unchanged
[ ] no consumer, commit or offset behaviour changed for a measurement
[ ] no new thread, task or lock was introduced by instrumentation
[ ] no second server, port or agent was added
[ ] tracing/OTel not introduced where the profile says disabled
```

## 11. Tests

```text
[ ] one test per terminal outcome, including cancellation and cleanup
[ ] a test asserts the redaction marker for a sensitive value
[ ] a test asserts label values come from the finite domain
[ ] a test asserts the terminal event fires exactly once on the failure path
```

## 12. Claims

```text
[ ] every runtime claim names the command or query that produced it
[ ] nothing is labelled runtime-reproduced that the reviewer did not run
[ ] no current-state claim rests on a profile, a plan or an old report
[ ] gaps are listed explicitly, not omitted
```
