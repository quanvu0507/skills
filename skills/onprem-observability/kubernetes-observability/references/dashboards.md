# Dashboards

## Five rules

1. **Query the actual runtime series first.** Before writing a panel, run the
   query against VictoriaMetrics and look at the result. A dashboard authored from
   the metric names in a plan renders empty, and an empty dashboard is
   indistinguishable from a broken deployment during an incident.

2. **The source JSON is authoritative.** The dashboard lives in Git. Editing in
   the Grafana UI produces a change that the next reconcile silently discards —
   and the person who made it believes it shipped.

3. **Source and generated ConfigMap change together, in one commit.** Otherwise
   the two disagree and nobody can tell which one is live.

4. **Handle the intentional empty state.** A panel with no data must be
   distinguishable from a panel that is broken. Use an explicit "No data" text and
   a documented reason — a service with no traffic at 03:00 is not an outage.

5. **Metrics-to-logs links preserve the time range and use bounded filters.** A
   drill-down that jumps to "now" loses the incident, and one that filters on an
   unbounded label produces a query that never returns.

## Panel review

```text
does the query return data right now, against the real backend?
is the aggregation correct — sum before divide, not divide before sum?
does rate() have a window of at least 4x the scrape interval?
are units set, and do they match the metric's unit?
is the legend readable without an identity label in it?
does the panel answer a question an operator actually asks during an incident?
```

That last point is the one most often skipped. A panel that exists because the
metric exists adds noise. Name the question each panel answers.

## Aggregation correctness

```promql
# Wrong: per-instance ratios averaged together are not the overall ratio.
avg(rate(errors_total[5m]) / rate(requests_total[5m]))

# Right: aggregate numerator and denominator, then divide.
sum(rate(errors_total[5m])) / sum(rate(requests_total[5m]))
```

Aggregate away instance identity with `sum without (instance, pod)` so a rollout
does not appear as a discontinuity in every panel.

## Metrics to logs

Link from a metric panel to Loki with the time range carried over and a bounded
label selector:

```logql
{namespace="$namespace", app="$service"} | json | level="ERROR"
```

The selector uses only infrastructure labels, which are bounded. High-cardinality
fields — request id, device id, correlation id — are matched **after** the `json`
parser, at query time. Putting them in the stream selector produces a query across
every stream in the tenant.

## Variables

Use template variables for namespace and service so one dashboard serves every
instance of a workload. Bound each variable's query so it cannot enumerate a
high-cardinality label. `label_values(up, namespace)` is fine;
`label_values(http_server_requests_total, request_id)` is a dashboard that hangs
the browser and loads the backend.

## Ownership

For `kubernetes-talos`, the GitOps repository owns both the dashboard source and
the generated ConfigMap. The application repository does not ship dashboards. If a
change requires both, sequence it: application first, then scrape, then dashboard,
each with its own evidence.

## Rollback

Revert the source JSON and the generated ConfigMap in the same commit. Reverting
only one leaves the deployed dashboard and the repository disagreeing, and the
next person cannot tell which is correct.
