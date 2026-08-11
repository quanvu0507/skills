# Rollout and evidence

## Evidence levels

Every factual claim about a system carries one of these labels:

```text
source-confirmed
runtime-evidence
inference
not-verified
```

| Level | Means | Requires |
|---|---|---|
| `source-confirmed` | read in the current source at a known revision | file path, line, revision |
| `runtime-evidence` | observed in a running system | the exact command or query and its output |
| `inference` | deduced from patterns, not observed | the reasoning and what would confirm it |
| `not-verified` | assumed | say so plainly |

The failure this prevents: reading instrumentation code and reporting that the
metric "is being collected". Source proves the code exists. It does not prove the
process is running the build, that the scrape is configured, that the target is
`up`, or that the series arrived. Those are four separate runtime facts.

A profile, a plan or a previous report is **never** evidence of current state.
Re-resolve current branch, current revision and current deployment status in every
session.

## Rollout order

```text
1. application change merged and deployed
2. collection configured (scrape target or log path) and verified
3. series or streams confirmed present in the backend
4. dashboard built against the confirmed series
5. baseline observed over a representative period
6. alert rules written against the baseline
7. alert delivery tested end to end
```

Skipping ahead produces predictable failures: a dashboard written before step 3
encodes metric names that do not exist and renders empty; an alert written before
step 5 has a threshold picked from imagination and either never fires or pages on
normal traffic.

## Rollback per layer

The layers are usually owned by different repositories, so "roll back the change"
is ambiguous. Write the rollback for each layer that the change touched:

| Layer | Rollback |
|---|---|
| application | redeploy the previous immutable image tag or digest |
| scrape / collection | revert the scrape or collector configuration |
| dashboard | revert the dashboard source **and** the generated artifact together |
| rules | remove or revert the rule, and confirm the receiver stopped firing |

A dashboard reverted without its generated artifact leaves the two out of sync and
the next person cannot tell which is authoritative.

## Alerting is not operational until all of it works

```text
baseline data exists over a representative period
the rule engine (vmalert) is enabled and evaluating
Alertmanager is enabled
a receiver is configured and owned by a named team
the rule is unit-tested against sample data
a synthetic alert was delivered end to end and observed by a human
```

Until the last line is true, alerting is **not** complete. Writing the rule file is
one step out of six. Reporting "alerts are configured" when the receiver is
missing produces a system that looks monitored and silently is not — worse than no
alerting, because no one is watching manually either.

## Single-replica rollout

When a service runs one replica, any rollout is an outage. That requires:

```text
a maintenance window agreed with the owner, or a documented acceptable gap
evidence the gap was acceptable in the previous rollout
a rollback that fits inside the same window
```

State this explicitly rather than treating the deployment as zero-downtime.

## Reporting template

```text
Claim:      <what is asserted>
Evidence:   source-confirmed | runtime-evidence | inference | not-verified
Source:     <file:line @ revision> or <command + output>
Gap:        <what would raise the evidence level>
Rollback:   <per affected layer>
```
