---
name: observability-review
license: Apache-2.0
compatibility: "Grafana OSS, Loki OSS, Alloy, VictoriaMetrics, Kubernetes/Talos, Docker, VM/systemd; no Grafana Cloud dependency"
description: "Evidence-based review of on-premises observability work — implementations, plans and response documents. Classifies every finding by evidence level, assigns severity from impact plus evidence, and produces findings, an acceptance matrix, a risk register and a recommended PR sequence. Use when reviewing an observability implementation against its plan, auditing metric cardinality or log safety, checking whether alerting is genuinely operational, or verifying claims about deployment and runtime state."
---

# Observability review

Reviews on-prem observability work and produces a report whose every claim is
labelled with how it is known. Read
[`observability-contract`](../observability-contract/SKILL.md) first — the contract
supplies the rules; this skill applies them.

## Method

```text
1. Resolve current state: repository, branch, exact revision. Never assume.
2. Read the requirements baseline: plan, design or issue being implemented.
3. Read the source at that revision.
4. Separate what the source proves from what only a running system can prove.
5. Reproduce what you can; ask for what you cannot.
6. Classify each finding: severity + evidence level.
7. Write the report in the fixed section order.
```

A profile, a plan or a previous report is **never** evidence of current runtime
state. If the exact revision cannot be resolved, say so in the report rather than
reviewing an unspecified version.

## Evidence taxonomy

```text
source-confirmed
runtime-evidence-supplied
runtime-reproduced
inference
not-verified
```

**A finding is never labelled `runtime-reproduced` unless the reviewer ran the
command against the target environment.** Evidence supplied by the author is
`runtime-evidence-supplied` — a different and weaker claim.

→ [`references/evidence-levels.md`](references/evidence-levels.md)

## Severity

```text
P0 = active security/data-loss emergency
P1 = production blocker or severe operational blind spot
P2 = important correctness/operability gap
P3 = improvement/design consistency
```

Severity requires **impact plus evidence**. Speculative impact alone cannot promote
a finding to P0 or P1. → [`references/severity-model.md`](references/severity-model.md)

## Report structure

```text
Executive summary
Reviewed revisions
Requirements baseline
Findings ordered by severity
Evidence classification
Validation matrix
Risk register
Recommended PR sequence
Rollback/evidence gaps
```

→ [`references/output-contract.md`](references/output-contract.md)

## Where the report goes

A report nobody can find later is a report nobody reads. Write it to a path
derived from the project's `artifacts.root`, which defaults to `docs/superpowers`:

```text
<artifacts.root>/reviews/YYYY-MM-DD-<slug>.md      this review
<artifacts.root>/validation/YYYY-MM-DD-<slug>.md   the validator's report
```

The project profile may override `artifacts.root`. Never invent a location per
session — six months on, nobody knows where the review of a given service went.

## What to check

→ [`references/review-rubric.md`](references/review-rubric.md) has the full rubric.
The failures that recur most:

| Check | Common failure |
|---|---|
| terminal recording | recorded on success only, so error rate reads zero during an outage |
| label cardinality | an identifier used as a label, unbounded by construction |
| log safety | payload, header or token reaching the log |
| route normalization | raw URI as a label, so clients control the label domain |
| readiness semantics | readiness fails on dependency health, so a partial outage becomes total |
| Kubernetes resources | `ServiceMonitor`/`PrometheusRule` in a VictoriaMetrics cluster — applies, reconciles nothing |
| alerting completeness | rule merged while `vmalert` or the receiver is absent |
| dashboard provenance | built before runtime series existed; renders empty |
| evidence | "metrics are collected" asserted from source alone |

## Two things this review must not do

**Do not recommend removing a unique Prometheus label without evidence.** A label
that looks redundant is often the only thing separating two series, and dropping it
silently merges them — the data is then wrong rather than missing. Require the
series-count query first.

**Do not emit a proprietary services disclaimer.** This review is internal work
product; boilerplate from a commercial engagement template does not belong in it.

## Reviewing a response document

When reviewing a reply to a previous review, check three things separately:

```text
was the finding actually addressed, or only argued against?
if disputed, does the response bring new evidence, or only reasoning?
does the claimed fix have its own evidence at the current revision?
```

A disagreement backed by a runtime query outranks a review backed by inference. A
disagreement backed only by assertion does not change the finding — record both
positions and the evidence each rests on.

## Verification before signing off

```text
every finding has a severity and an evidence level
every runtime claim names the command or query that produced it
no claim of completion for alerting without receiver delivery evidence
the validation matrix lists what was not verified, not only what passed
the PR sequence is ordered by dependency, not by convenience
```
