# Evidence levels

## The five values

```text
source-confirmed
runtime-evidence-supplied
runtime-reproduced
inference
not-verified
```

| Level | Means | Must record |
|---|---|---|
| `source-confirmed` | read in the source at a known revision | file path, line, revision |
| `runtime-evidence-supplied` | the author provided output from a running system | who supplied it, when, against which environment |
| `runtime-reproduced` | **the reviewer** ran it against the target environment | the exact command or query, its output, when |
| `inference` | deduced from patterns, not observed | the reasoning and what would confirm it |
| `not-verified` | assumed or unchecked | say so plainly |

## The distinction that matters most

`runtime-reproduced` requires that **you** ran the command. Author-supplied output
is `runtime-evidence-supplied`, which is weaker for reasons that are not about
trust: it may come from a different environment, a different revision, a different
time, or a moment when a temporary condition was in effect.

Labelling supplied evidence as reproduced is the single most damaging error in this
report format, because it makes an unverified claim look verified and nobody
re-checks it.

## What source can and cannot prove

Source proves the code exists. It does not prove:

```text
the running process is built from that revision
the scrape or log path is configured
the target is up
the series or streams actually arrived
the dashboard queries return data
the alert rule is loaded and evaluating
the receiver would deliver
```

Those are seven separate runtime facts. "The metric is being collected" asserted
from source alone is `inference`, and should be written as such.

## Raising a level

Each finding records what would raise its evidence level:

```text
Claim:  the Kafka lag metric is exported
Level:  source-confirmed (Consumer.scala:142 @ a1b2c3d)
Gap:    no scrape output; to reach runtime-reproduced, run
        curl -s localhost:9000/metrics | grep kafka_consumer_lag_records
        against a running instance of that revision
```

A reader can then close the gap without re-deriving the whole finding.

## Conflicts between source and runtime

When source and runtime disagree, **runtime wins for current state** and source
wins for intent. Record both, and state the most likely cause:

```text
the deployed revision differs from the one reviewed
configuration overrides the code path
a feature flag is off
the change was reverted downstream
```

Do not resolve the conflict by choosing the more convenient answer. Record it as an
open item with the specific check that would settle it.

## Reproducing safely

Prefer read-only commands. When a check would modify state — firing a synthetic
alert, restarting a component — record it as a requested action for the owner
rather than performing it. A review that causes an incident is not a review.

## Recording template

```text
Finding:    <one sentence>
Severity:   P0 | P1 | P2 | P3
Evidence:   source-confirmed | runtime-evidence-supplied | runtime-reproduced | inference | not-verified
Source:     <file:line @ revision> or <command + output + timestamp>
Impact:     <what breaks, for whom, when>
Gap:        <what would raise the evidence level>
Fix:        <smallest change that resolves it>
Owner:      <repository or team>
```
