# Validation matrix — <subject>

Every row needs a command or query, not an opinion. A row with no evidence belongs
in the "not verified" column, not in the pass column.

**Revision under validation:** `<full SHA>`
**Environment:** `<profile> / <cluster or host>`
**Validated at:** `<timestamp>`

## Application

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| service builds and tests pass | | all green | | |
| terminal outcome recorded on success | | 1 record | | |
| terminal outcome recorded on failure | | 1 record | | |
| terminal outcome recorded on cancellation/timeout | | 1 record | | |
| redaction marker present for sensitive field | | marker, not value | | |
| log line parses as JSON with expected fields | | valid JSON | | |

## Collection

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| scrape resource exists | | present | | |
| target is up with a recent scrape | `up{job=~"..."}` | 1 | | |
| expected metric families present | `count by (__name__) (...)` | full list | | |
| series count within budget | `count(<metric>)` | ≤ budget | | |
| no unexpected label appears | `count by (<label>) (<metric>)` | finite | | |
| log stream arrives in Loki | LogQL selector | non-empty | | |

## Exposure

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| `/metrics` refused from outside | `curl -o /dev/null -w '%{http_code}'` | 401/403/404 | | |
| `/health` refused from outside | | 401/403/404 | | |
| `/metrics` reachable from inside | | 200 | | |

## Health

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| `/ready` 503 before init, 200 after | | as stated | | |
| dependency outage does not change `/ready` | | unchanged | | |
| liveness performs no dependency call | | constant time | | |

## Dashboards

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| every panel query returns data | | non-empty | | |
| source and generated artifact in one commit | | same commit | | |
| logs link carries time range | | preserved | | |

## Alerting

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| baseline observed | | recorded range | | |
| rule engine running | | present | | |
| Alertmanager running | | present | | |
| receiver configured and owned | | named team | | |
| rule loaded and evaluating | | listed | | |
| synthetic alert delivered | | human confirmed | | |

## Rollout

| Check | Command / query | Expected | Result | Evidence level |
|---|---|---|---|---|
| image pinned to tag or digest | | immutable | | |
| single-replica outage window agreed | | documented | | |
| rollback tested for each layer | | documented | | |

## Not verified

| Check | Why not | What would verify it | Owner |
|---|---|---|---|

Evidence levels: `source-confirmed`, `runtime-evidence-supplied`,
`runtime-reproduced`, `inference`, `not-verified`.
