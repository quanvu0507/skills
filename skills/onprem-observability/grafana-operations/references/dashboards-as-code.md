# Dashboards as code

## Source of truth

The dashboard JSON in Git is authoritative. The deployed artifact — a ConfigMap, a
provisioning file — is generated from it, and **both change in the same commit**.
When they diverge, nobody can tell which is live, and the next person to edit picks
one at random.

A change made in the Grafana UI is discarded at the next reconcile. Anyone who needs
to explore interactively should do so and then port the result back to the source
file, deliberately.

## Validate against real series

Before a panel is committed:

```text
1. Run the query against the real backend.
2. Confirm it returns data, and that the shape is what the panel expects.
3. Record the query and its result.
```

A dashboard authored from the metric names in a plan renders empty, and an empty
dashboard is indistinguishable from a broken deployment — during an incident, that
costs the first ten minutes.

## Correctness

```promql
# Wrong: per-instance ratios averaged are not the overall ratio.
avg(rate(errors_total[5m]) / rate(requests_total[5m]))

# Right: aggregate both sides, then divide.
sum(rate(errors_total[5m])) / sum(rate(requests_total[5m]))
```

```text
rate() windows at least 4x the scrape interval
aggregate away instance identity: sum without (instance, pod)
histogram quantiles via histogram_quantile over _bucket, never avg
units set on every panel, matching the metric's unit
a guard on any divide whose denominator can legitimately be zero
```

## The empty state

A panel with no data must be visually distinct from a broken panel, and the
legitimate no-data case must be documented. "No traffic at 03:00" is not an outage,
but a blank panel says nothing about which it is. Set explicit "No data" text that
explains the expected reason.

## Metrics to logs

Link from a metric panel to Loki carrying the **current time range** — a link that
jumps to "now" loses the incident being investigated — and a bounded stream
selector:

```logql
{namespace="$namespace", app="$service"} | json | level="ERROR"
```

The selector uses only bounded infrastructure labels. High-cardinality matching
happens after `| json`, at query time. A selector containing a request id or a
device id queries every stream in the tenant and does not return.

## Template variables

Variables make one dashboard serve every instance of a workload. Bound each one:

```text
good: label_values(up, namespace)
good: label_values(up{namespace="$namespace"}, job)
bad:  label_values(http_server_requests_total, request_id)
```

The bad case hangs the browser and loads the backend. Chain variables so each is
filtered by the previous one.

## Panel purpose

Every panel answers a question an operator asks during an incident. A panel that
exists because the metric exists is noise, and noise on the first screen is what
makes people stop opening the dashboard. The first screen should answer "is it
healthy?" without scrolling.

## Rollback

Revert the source JSON and the generated artifact in the same commit. Reverting one
leaves the deployed dashboard and the repository disagreeing.
