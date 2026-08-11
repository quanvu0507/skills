# Cardinality and verification

## Why this is a shared concern

VictoriaMetrics is normally shared across teams. Cardinality is the resource that
runs out, and it runs out globally: one service adding an unbounded label slows
queries and ingestion for everyone. Treat the series budget as a contract with the
other tenants, not as an internal detail.

## Compute before you add

Series count for a metric is the product of its label domain sizes.

```text
method(5) x route(24) x status_class(4) x outcome(2) = 960 series
```

If a domain cannot be counted, it is not finite and must not be a label. "It is
only 50 devices today" is not a count — it is a snapshot of a number that grows.

## Finding an existing problem

```promql
# Which metric families have the most series?
topk(20, count by (__name__) ({__name__=~".+"}))

# Which values does a suspicious label take?
count by (<label>) (<metric>)

# Is a target's sample count growing without a traffic increase?
scrape_samples_scraped{job="example-service"}
```

`scrape_samples_scraped` rising while request rate is flat is the signature of a
label whose domain is growing. It shows up long before anyone notices a slow query.

## Before removing a label

**Never remove a unique label because it looks redundant.** Removing a label that
distinguishes two series merges them, and the merged data is *wrong* rather than
missing — silently, and retroactively in every panel that used it.

Check first:

```promql
count by (<label>) (<metric>)     # how many distinct values?
count(<metric>) without (<label>) # does removal change the series count?
```

If removal changes the count, the label carries information. Removal then requires
a stated decision about which data is being given up, not a cleanup commit.

## Verifying a new metric end to end

```text
1. The endpoint exposes it:   curl the scrape path on a running instance.
2. The scrape succeeds:       up{job="..."} == 1, recent scrape.
3. The series exist:          query the metric name; confirm the label set.
4. The domain is as designed: count by (<label>) (<metric>) matches the inventory.
5. A consumer uses it:        a dashboard panel or a rule references it.
```

Record each step's command and output as runtime-evidence. Steps 1 and 2 are
different facts — an endpoint that responds is not a scrape that succeeded.

## Staleness

When an instance disappears, its series go stale and stop returning after the
staleness window. That is expected. What is not expected is series identity
changing on every rollout — if it does, an ephemeral identifier is in the label set,
usually introduced by relabeling.

## Churn

Churn — new series appearing and old ones going stale continuously — is worse than
a high but stable series count, because the index grows without the query surface
shrinking. Pod name churn on rollout is acceptable. Per-request or per-entity churn
is not.

## Ongoing review

```text
monthly: top metric families by series count
monthly: metrics with no dashboard panel and no rule
on change: recompute expected series when a label domain grows
on incident: check scrape_samples_scraped before blaming query performance
```
