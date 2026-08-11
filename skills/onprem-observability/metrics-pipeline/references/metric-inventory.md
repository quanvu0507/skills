# Metric inventory

Fill this in **before** writing instrumentation code. The point is the expected
series count: computing it takes a minute and catches an unbounded label that would
otherwise become a shared-infrastructure incident.

## Required fields per metric

```text
name              follows <namespace>_<subsystem>_<name>_<unit>
type              counter | gauge | histogram
unit              base units: seconds, bytes, requests
help              one line, states what is measured
labels            each with its domain and the domain's size
expected_series   product of all label domain sizes
recorded_at       the boundary where the terminal record happens
consumer          the dashboard panel or rule that uses it
owner             the team responsible
```

## Template

```yaml
- name: http_server_requests_total
  type: counter
  unit: requests
  help: Terminal HTTP request outcomes
  labels:
    method: { domain: [GET, POST, PUT, PATCH, DELETE], size: 5 }
    route: { domain: route-template-list, size: 24 }
    status_class: { domain: ["2xx", "3xx", "4xx", "5xx"], size: 4 }
    outcome: { domain: [success, failure], size: 2 }
  expected_series: 960
  recorded_at: request-terminal-boundary
  consumer: dashboard/service-overview
  owner: example-service
```

For a histogram, remember each bucket is a series: multiply by bucket count plus
two (`_sum` and `_count`). A histogram with seven buckets and 120 label
combinations is 1,080 series, not 120.

## Rejected labels

Keep a list of labels that were proposed and rejected, with the reason. Without it
the same proposal returns every few months and someone eventually accepts it.

```yaml
rejected_labels:
  - name: request_id
    reason: one series per request; belongs in the log line
  - name: uri
    reason: unbounded and client-controlled; use the route template
  - name: exception_message
    reason: unbounded free text; classify into a finite error_kind
  - name: device_id
    reason: entity identity; query logs instead
```

## Budget

```yaml
review:
  total_expected_series: 1940
  series_budget: 5000
  reviewed_by: ""
  reviewed_at: ""
```

Agree the budget with whoever operates VictoriaMetrics. It is shared capacity, and
a service that exceeds its budget affects every other tenant.

## Naming stability

A metric name is a public API. Renaming one silently breaks every dashboard, alert
and recording rule that referenced it — nothing errors, panels simply go blank.
Rename through a deprecation window with both names emitted, and record the removal
date in the inventory.

## Review triggers

Revisit the inventory when:

```text
a route is added (the route domain grew)
a new outcome value is introduced
a histogram's buckets change
scrape_samples_scraped rises without a traffic increase
a dashboard panel or rule is deleted (its metric may now have no consumer)
```

## Metrics with no consumer

A metric that no dashboard and no rule uses answers no question and costs
cardinality forever. Either add the consumer or remove the metric. Reviewing this
periodically is what keeps a metrics backend healthy over years.
