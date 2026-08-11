# Dashboard review checklist

Copy into the review. Every line needs an answer, not a tick.

## Data exists

```text
[ ] every panel query was run against the real backend and returned data
[ ] the exact queries and their results are recorded as runtime-evidence
[ ] metric names in the dashboard match the names the service actually emits
[ ] the dashboard's time range default shows a period that has data
```

## Correctness

```text
[ ] ratios aggregate numerator and denominator before dividing
[ ] rate() windows are at least 4x the scrape interval
[ ] instance identity is aggregated away (sum without (instance, pod))
[ ] units are set on every panel and match the metric's unit
[ ] histogram quantiles use histogram_quantile over _bucket, not avg
[ ] no panel divides by a value that can legitimately be zero without a guard
```

## Cardinality and cost

```text
[ ] no template variable enumerates a high-cardinality label
[ ] no query selects on request id, correlation id, device id or user id
[ ] the heaviest query was timed and is acceptable at the default range
```

## Empty state

```text
[ ] a panel with no data is visually distinct from a broken panel
[ ] the legitimate no-data case is documented (e.g. no traffic overnight)
[ ] "No data" text explains what it means rather than showing a blank panel
```

## Logs navigation

```text
[ ] metrics-to-logs links carry the current time range
[ ] the LogQL stream selector uses only bounded infrastructure labels
[ ] high-cardinality matching happens after | json, at query time
[ ] the link lands on a query that returns within a few seconds
```

## Ownership and lifecycle

```text
[ ] the dashboard source JSON is in the GitOps repository
[ ] source and generated ConfigMap are updated in the same commit
[ ] no edit was made in the Grafana UI (it would be silently reconciled away)
[ ] the rollback reverts both source and generated artifact together
[ ] an owner is named for the dashboard
```

## Purpose

```text
[ ] each panel answers a question an operator asks during an incident
[ ] panels that exist only because the metric exists were removed
[ ] the first screen answers "is it healthy?" without scrolling
```

## Evidence

| Check | Evidence level | Source |
|---|---|---|
| queries return data | | |
| no high-cardinality selector | | |
| logs link works | | |
| source and ConfigMap in sync | | |

Evidence levels: `source-confirmed`, `runtime-evidence`, `inference`,
`not-verified`.
