# Alerting operations

## The six gates

```text
baseline data
rule engine enabled and evaluating
Alertmanager enabled
receiver configured with a named owner
rule tested against sample data
synthetic delivery observed by a human
```

Report the status of each with evidence. A merged rule file with no engine running
is a file, not an alert — and a system described as monitored while nothing is
watching is worse than one known to be unmonitored, because nobody checks manually
either.

## Baseline first

A threshold chosen before a baseline exists is a guess, and it will either never
fire or page on normal traffic.

```promql
quantile_over_time(0.99, http_server_request_duration_seconds_bucket[7d])
```

Observe a period that includes the system's real variation — the nightly batch, the
weekly peak — and record the observed range with the query that produced it.

## Rule shape

```text
for:            always set; without it a single scrape blip pages someone
no-traffic:     a ratio with zero denominator is NaN — decide explicitly whether
                no traffic is itself an alert, and make that a separate rule
aggregation:    aggregate before dividing, never per-instance ratios summed
severity:       critical | warning | info, from impact plus evidence
runbook:        every alert links to one
```

An alert without a runbook is a notification nobody knows how to act on, which
trains the recipient to ignore the channel.

## Severity

| Severity | Meaning | Routing |
|---|---|---|
| `critical` | user-visible failure or imminent data loss | page now |
| `warning` | degradation needing attention within a working day | ticket or channel |
| `info` | context during an incident | never paged |

Severity follows impact plus evidence. Speculative worst cases do not justify
`critical`; over-severe alerts are how a team learns to ignore alerts.

## Receivers

A route with no receiver, or a receiver pointing at an unmonitored mailbox, is
identical to no alert. Record for each:

```text
receiver name
destination
the team that owns it
who is on call, and how they are reached out of hours
```

## Synthetic delivery test

This is the only check that proves routing, grouping, inhibition, silencing and the
receiver work together. Fire one alert end to end, have a human confirm receipt, and
record what was fired, when, who received it and how it was resolved.

Re-run it after any change to routing, receivers or the Alertmanager configuration.
This part regresses silently: everything looks configured, and nothing is delivered.

## Silences

```text
every silence has an expiry — never indefinite
every silence has a reason and an owner
review active silences periodically
```

An indefinite silence created during an incident and never removed is
indistinguishable from an alert that does not work.

## Grafana alerting or vmalert

Both are legitimate. Choose one per rule domain and say which, because two engines
evaluating overlapping rules produce duplicate pages that nobody can trace.

Provision rules from files either way, and reference the same datasource UIDs the
dashboards use.

## Rollback

```text
remove or revert the rule file
confirm the engine no longer lists the rule
confirm the receiver stopped firing
```

Rules roll back independently of the application. "Revert the deployment" leaves
the rule in place and firing.
