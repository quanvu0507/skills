# VMRule rollout

## Alerting is not complete until all six gates pass

```text
baseline data
vmalert enabled
Alertmanager enabled
receiver configured
rule test
synthetic delivery
```

Writing the rule file is one gate out of six. A merged `VMRule` in a cluster where
`vmalert` is not running is a file, not an alert. Reporting "alerting is
configured" at that point produces a system that appears monitored and is not —
which is worse than no alerting, because nobody is watching manually either.

State the status of each gate explicitly, with evidence, before using the word
"done".

## Gate 1 — baseline

A threshold picked before a baseline exists is a guess. Observe the metric over a
period that includes the system's normal variation — a nightly batch, a weekly
peak — and record the observed range.

```promql
quantile_over_time(0.99, http_server_request_duration_seconds_bucket[7d])
```

Record the query and its result. Without it, the threshold's provenance is
`not-verified` and the first busy night will page.

## Gate 2 and 3 — the platform must be running

```bash
kubectl -n <monitoring-ns> get vmalert
kubectl -n <monitoring-ns> get pods -l app.kubernetes.io/name=alertmanager
```

Enabling `vmalert` and Alertmanager is a **platform task**, usually owned by a
different repository and a different team than the application. If they are
disabled, the correct output is a dependency, not an alert rule that quietly does
nothing.

## Gate 4 — a receiver with a named owner

A route with no receiver, or a receiver pointing at an unmonitored mailbox, is the
same as no alert. Record the receiver and the team that owns it.

## Gate 5 — rule shape and test

```yaml
apiVersion: operator.victoriametrics.com/v1beta1
kind: VMRule
metadata:
  name: <service>
spec:
  groups:
    - name: <service>.rules
      rules:
        - alert: ServiceErrorRateHigh
          expr: |
            sum(rate(http_server_requests_total{service="<service>",outcome="failure"}[5m]))
              /
            sum(rate(http_server_requests_total{service="<service>"}[5m]))
              > 0.05
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Error ratio above 5% for <service>"
            runbook_url: "<internal runbook location>"
```

Rule review points:

- **`for:` is not optional.** Without it a single scrape blip pages someone.
- **Guard the divide.** A ratio with no traffic evaluates to `NaN`; decide whether
  no traffic is itself an alert, and if so make it a separate rule with a clear
  name rather than an accident of the ratio.
- **Aggregate before dividing**, not after — per-instance ratios summed together
  are not the overall ratio.
- **Every alert has a runbook.** An alert without one is a notification nobody
  knows how to act on.

Test the expression against recorded data before merging.

## Gate 6 — synthetic delivery

Force one alert end to end and have a human confirm receipt. This is the only gate
that proves routing, silencing, inhibition and the receiver all work together.

Record: what was fired, when, who received it, and how it was resolved.

## Severity

| Severity | Meaning |
|---|---|
| `critical` | user-visible failure or imminent data loss; page now |
| `warning` | degradation that needs attention within a working day |
| `info` | context for an incident; never routed to a pager |

Severity must follow impact plus evidence. A speculative worst case does not
justify `critical` — over-severe alerts train responders to ignore the channel.

## Rollback

```text
remove or revert the VMRule
confirm vmalert no longer lists the rule
confirm the receiver stopped firing
```

Rules roll back independently of the application. Say so explicitly, because a
"revert the deployment" instruction leaves the rule in place.
