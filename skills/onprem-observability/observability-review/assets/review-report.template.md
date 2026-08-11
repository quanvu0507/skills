# Observability review — <subject>

**Reviewer:** <name>
**Date:** YYYY-MM-DD
**Release position:** release | release with follow-ups | blocked

## Executive summary

<Three to six sentences. What was reviewed, whether it is releasable, and the most
important finding. Name the finding IDs that drive the release position.>

## Reviewed revisions

```text
repository        <name>
branch            <name>
revision          <full SHA>
reviewed at       <timestamp>
environment       <profile> / <cluster or host if runtime evidence was taken>
related revisions <other repositories touched>
```

## Requirements baseline

<Link to the plan, design or issue. State what the change was supposed to achieve.>

## Findings

### F-01 — <one-line title>

```text
Severity:  P0 | P1 | P2 | P3
Evidence:  source-confirmed | runtime-evidence-supplied | runtime-reproduced | inference | not-verified
Source:    <file:line @ revision>  or  <command + output + timestamp>
Impact:    <what breaks, for whom, when>
Gap:       <what would raise the evidence level>
Fix:       <smallest change that resolves it>
Owner:     <repository or team>
```

<Repeat per finding, ordered by severity then evidence strength.>

## Evidence classification

| ID | Claim | Level | Source |
|---|---|---|---|
| F-01 | | | |

## Validation matrix

| Check | Result | Evidence | Not verified because |
|---|---|---|---|
| terminal outcome recorded on every path | | | |
| label domains finite; series count within budget | | | |
| no credential or payload in logs | | | |
| scrape target up; expected series present | | | |
| management paths refused from outside | | | |
| dashboard queries return data | | | |
| rule engine and receiver enabled | | | |
| synthetic alert delivered | | | |
| business ordering unchanged | | | |
| rollback documented per layer | | | |

## Risk register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|

## Recommended PR sequence

```text
1. <repo> <change>   (F-xx)
2. <repo> <change>   (F-xx)
```

<Note any step blocked by another team.>

## Rollback and evidence gaps

```text
rollback — application:
rollback — scrape/collection:
rollback — dashboard:
rollback — rules:

not verified:
would be verified by:
re-check after deployment:
```
