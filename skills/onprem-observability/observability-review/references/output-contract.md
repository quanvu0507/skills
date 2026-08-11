# Output contract

## Where the file goes

```text
<artifacts.root>/reviews/YYYY-MM-DD-<slug>.md
```

`artifacts.root` comes from the project profile and defaults to `docs/superpowers`.
The slug names what was reviewed, not who reviewed it.

The location is part of the output contract, not a detail left to the session. A
review written to an ad-hoc path is unfindable the moment the session ends, and
the next reviewer starts from nothing.

## Fixed section order

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

The order is fixed so a reader can find the same thing in the same place across
reviews, and so the sections that are usually skipped — gaps and rollback — cannot
quietly disappear.

## Executive summary

Three to six sentences. What was reviewed, whether it is releasable, and the single
most important finding. No preamble, no restating the task.

State the release position explicitly: `release`, `release with follow-ups`, or
`blocked`, plus the finding IDs that drive it.

## Reviewed revisions

```text
repository        <name>
branch            <name>
revision          <full SHA>
reviewed at       <timestamp>
environment       <profile name> / <cluster or host, if runtime evidence was taken>
related revisions <other repositories touched by this change>
```

If a revision could not be resolved, say so here. A review of an unspecified
version cannot be re-checked later.

## Requirements baseline

What the change was supposed to do, with a link to the plan, design or issue. A
finding of "missing" only means something against a stated requirement; without
this section, every gap becomes an opinion.

## Findings

One block per finding, ordered by severity then by evidence strength:

```text
F-01  P1  Error rate is recorded on the success path only
Evidence:  source-confirmed — HttpMetrics.scala:88 @ a1b2c3d
Impact:    During an outage the failure counter stays flat, so the error-rate
           panel and any alert built on it read healthy.
Gap:       runtime-reproduced requires forcing a 5xx and re-scraping.
Fix:       Record in a combinator that observes both outcomes.
Owner:     <application repository>
```

Use stable IDs. The response document and the follow-up PRs will reference them.

## Evidence classification

A table of every claim with its level, so a reader can see at a glance how much of
the report is observed and how much is inferred:

| ID | Claim | Level | Source |
|---|---|---|---|

## Validation matrix

What was checked, what passed, and — the part usually omitted — **what was not
verified**:

| Check | Result | Evidence | Not verified because |
|---|---|---|---|

A matrix that lists only passes is a marketing document. The "not verified" column
is what makes the review honest and tells the next reviewer where to start.

## Risk register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|

Only risks that survive the findings. A risk already captured as a finding does not
need a second row.

## Recommended PR sequence

Ordered by dependency, not convenience, with the owning repository named:

```text
1. <repo> fix terminal recording on the failure path                (F-01)
2. <repo> remove the unbounded label and confirm the series count   (F-02)
3. <repo> add the scrape resource; confirm target up                (F-04)
4. <repo> dashboard, only after step 3 produces series              (F-06)
5. <platform repo> enable the rule engine and receiver              (F-08)
6. <repo> alert rules and synthetic delivery test                   (F-08)
```

State which steps are blocked by another team, so nobody waits on the wrong thing.

## Rollback and evidence gaps

```text
rollback per layer: application, scrape, dashboard, rules
what could not be verified, and exactly what would verify it
what must be re-checked after deployment
```

## Rules for the whole document

```text
every claim carries an evidence level
nothing is labelled runtime-reproduced that the reviewer did not run
no completion claim for alerting without receiver delivery evidence
no proprietary services disclaimer — this is internal work product
no private endpoint, credential or incident detail beyond what the reader needs
findings reference file:line at a revision, not "somewhere in the codebase"
```
