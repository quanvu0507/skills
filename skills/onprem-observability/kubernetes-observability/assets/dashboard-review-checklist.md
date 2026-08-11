# Dashboard review checklist

Copy into the review. Every line needs an answer, not a tick.

## 0. Read before you judge

```text
[ ] read each panel's description BEFORE concluding its query is wrong
[ ] where a description explains a choice, treat that as the author's reasoning
    and argue against it explicitly — do not silently overrule it
[ ] when a description and a document in docs/ disagree, the description is
    usually NEWER; verify which, and say which you used
[ ] where a description states the panel's PURPOSE, check the query achieves it
    in every case, not only the common one — a gap between the stated purpose and
    the query's behaviour is a finding, and usually a good one
```

The last line is the reason this section produces findings rather than only
suppressing false ones. A panel built to surface a specific failure, whose query
returns No data in the worst variant of that same failure, is broken in the way
that matters and looks fine in every other way.

This section is first because skipping it produces most false findings. In a
mature repository the reasoning lives next to the query, and a reviewer who reads
only the expression re-derives a decision that was already made and documented.

## 1. Compare with sibling dashboards

```text
[ ] list the other dashboards in this repository that cover the same shape of data
[ ] for each shared metric family, diff the label filters between them
[ ] any filter present in siblings and absent here is a finding until explained
[ ] any filter present here and absent in siblings is a finding in the sibling
[ ] match metric names in full and anchored — a substring search for `up{` also
    matches `component_up{` and manufactures empty findings
```

Expect part of this section's output to be differences that are correct on
inspection: a limit gauge that needs no pod filter because the limit is identical
across a workload's replicas, for example. Argue those away in writing rather
than dropping them silently — the reasoning is what makes the next reviewer
faster.

Repository-wide conventions are invisible to a rule that reads one file. The
highest-value findings usually come from this section, not from a general rule —
one dashboard missing a filter its siblings all carry is a defect, and no
standalone check can see it.

Example: `container_*` metrics are emitted by the kubelet on more than one path.
If two dashboards filter by the scrape path and a third does not, the third
double-counts. Nothing in the third file looks wrong on its own.

## 2. Metric provenance — checkable from source

Do this **before** the sections that need a live backend. It is verifiable from
the repository alone, so a reviewer without cluster access must not skip it.

```text
[ ] every metric name in the dashboard appears in the scrape configuration,
    the application's instrumentation, or a recording rule
[ ] label filters match the labels the scrape actually produces, including any
    the collector renames or prefixes
[ ] metrics whose availability is version-dependent name the version, and the
    deployed version is confirmed from the values or manifest in this repository
[ ] a metric the dashboard queries but nothing emits is a finding, even without
    a live query
```

## 3. Data exists — needs the real backend

```text
[ ] every panel query was run against the real backend and returned data
[ ] the exact queries and their results are recorded as runtime-evidence
[ ] the dashboard's default time range shows a period that has data
```

If you cannot reach the backend, record every line here as `not-verified` with
the query that would settle it. Do not mark them passed from source.

## 4. Time windows and the datasource

Two different things live in a range selector. Judge them separately — conflating
them is what makes this section either useless or noisy.

**Resolution** — how finely a rate is computed. This one does depend on the
scrape interval:

```text
[ ] every rate()/irate()/increase() that should follow the panel's time range
    uses $__rate_interval
[ ] $__interval on a Prometheus counter is a finding: it has no floor at the
    scrape interval, so at wide time ranges the window collapses below a single
    scrape and the panel empties — on exactly the panels worth alerting on
[ ] the datasource declares jsonData.timeInterval equal to the scrape interval,
    so $__rate_interval and $__interval have a real floor
```

Exception: in a Loki query `$__interval` is the step and carries no such defect.
Check the datasource type before flagging.

**Span** — a fixed period the panel is *about*: restarts in the last 24h, errors
in the last hour, a traffic gate. This has nothing to do with the scrape interval:

```text
[ ] a literal window is declared where the reader sees it — the panel TITLE
    counts, and is usually the clearest place
[ ] a literal window that appears in neither the title nor the description is a
    finding: the reader cannot tell what period the number covers
```

**Do not ask a semantic span to be "justified against the scrape interval".** A
panel titled `Restart (24h)` has already said what `[24h]` means; demanding a
sentence in the description repeats what the title states plainly.

**Do not check "the window is at least 4x the scrape interval".** `$__rate_interval`
satisfies it by definition, so the check ticks PASS and misses
`increase(...[$__interval])` — the defect it exists to catch.

## 5. Correctness

```text
[ ] ratios aggregate numerator and denominator before dividing
[ ] histogram quantiles use histogram_quantile over _bucket, not avg
[ ] units are set on panels that display a measured quantity
[ ] no panel divides by a value that can legitimately be zero without a guard
```

Two rules that produce false findings if applied mechanically:

**`sum(rate(x_sum)) / sum(rate(x_count))` is not a missing guard.** It is the
standard mean-from-histogram, normally paired with `histogram_quantile` panels.
With no traffic it yields no data, which is the correct display.

**Units do not apply to every panel.** Log panels, tables, and identity or state
panels such as `build_info` have no measured quantity. Check units on panels that
show one.

## 6. Aggregation: it depends on what the panel answers

```text
[ ] rate, ratio and throughput panels aggregate instance identity away
    (sum without (instance, pod)) so a rollout is not a discontinuity
[ ] resource and saturation panels DO split by pod — that is how one bad replica
    is found, and aggregating it away removes the panel's purpose
[ ] per-pod panels keep the legend readable and bound the replica count
```

Applying "aggregate identity away" to a heap, CPU, memory or thread panel is a
false finding. The rule exists so a `rate()` does not break across a deployment
boundary; it says nothing about per-replica resource views.

## 7. Target health

```text
[ ] a panel shows up{job="..."} for this service
[ ] losing a scrape target is visually distinct from the service having no traffic
[ ] where a service also exports its own readiness or component gauge, both are
    shown and the description says which answers which question
```

Without this, a dead scrape target and an idle service look identical: every panel
empty. That has a real cost — a scrape config pointing at a path that returns 404
produces exactly this picture, and nothing on the dashboard says so.

## 8. Cardinality and cost

```text
[ ] no template variable enumerates a high-cardinality label
[ ] no query selects on request id, correlation id, device id or user id
[ ] the heaviest query was timed and is acceptable at the default range
[ ] the expected series count for any per-route histogram is written down
```

**Never propose removing a label before counting it.** Run
`count by (<label>) (<metric>)` first. A label that looks redundant may be the only
thing separating two series; removing it merges them, and the data becomes wrong
rather than missing.

## 9. Empty state

```text
[ ] a panel with no data is visually distinct from a broken panel
[ ] the legitimate no-data case is documented (e.g. no traffic overnight)
[ ] "No data" text explains what it means rather than showing a blank panel
```

Apply this to panels where empty is expected and meaningful — an overnight job, a
"time since last commit" stat. Requiring it on every panel is noise.

## 10. Logs navigation

```text
[ ] metrics-to-logs links carry the current time range
[ ] the LogQL stream selector uses only bounded infrastructure labels
[ ] high-cardinality matching happens after | json, at query time
[ ] the link lands on a query that returns within a few seconds
```

A log panel embedded in the same dashboard inherits the time range automatically
and satisfies this section — it is not a missing link.

## 11. Ownership and lifecycle

```text
[ ] the dashboard source JSON is in the owning repository
[ ] source and generated artifact are updated in the same commit
[ ] every generated artifact has a corresponding source file
[ ] no edit was made in the Grafana UI (it would be silently reconciled away)
[ ] the rollback reverts both source and generated artifact together
[ ] an owner is named for the dashboard
```

A generated artifact with no source is a finding unless **both** hold: its
provenance is recorded (upstream id, version, fetch command) **and** it can be
regenerated in this environment.

A note alone is not enough. Provenance answers "where did this come from";
reproducibility answers "can we rebuild it". A dashboard whose regeneration needs
network egress this environment blocks is not reproducible whatever its note
says, and that gap belongs in the report rather than being waved through.

## 12. Purpose

```text
[ ] each panel answers a question an operator asks during an incident
[ ] panels that exist only because the metric exists were removed
[ ] the first screen answers "is it healthy?" without scrolling
```

## Evidence

| Check | Evidence level | Source |
|---|---|---|
| metric provenance | | |
| sibling comparison | | |
| time windows and datasource | | |
| target health panel present | | |
| queries return data | | |
| no high-cardinality selector | | |
| source and generated artifact in sync | | |

Evidence levels: `source-confirmed`, `runtime-evidence-supplied`,
`runtime-reproduced`, `inference`, `not-verified`.

Sections 0, 1, 2, 4, 6, 7, 11 are checkable from the repository alone. Section 3
and the timing line in section 8 need the backend. Say which you had.
