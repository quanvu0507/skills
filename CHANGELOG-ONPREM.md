# Changelog — on-prem fork delta

Upstream `grafana/skills` changes are not listed here; see the upstream repository.
This file records only the fork's own delta.

Change classes: `upstream-sync`, `generic-skill`, `private-profile`,
`trigger-breaking`, `security`, `installer`, `benchmark`.

## upstream-0.1.0-onprem.3

**generic-skill** — dashboard review checklist and rubric rewritten after running
them against three real dashboards. Nine defects, found by the reviewer that used
them rather than by inspection:

*Rules that produced false findings.* "Aggregate instance identity away" was
applied to heap, CPU, memory and thread panels — resource panels **must** split by
pod, or one bad replica is invisible. "No divide without a guard" flagged
`sum(rate(x_sum))/sum(rate(x_count))`, the mean-from-histogram idiom. "Units on
every panel" flagged log, table and identity panels that have no measured
quantity.

*A rule that passed over the case it existed to catch.* "rate() windows at least
4x the scrape interval" is satisfied by `$__rate_interval` by definition, so it
ticked PASS and missed `increase(...[$__interval])` — which collapses below the
scrape interval at wide ranges and empties the panel. Replaced with: every range
selector is `$__rate_interval`; a literal window or `$__interval` must be
justified; and the datasource must declare `timeInterval` so `$__interval` has a
floor.

*A rule in the wrong section.* Metric provenance sat under "Data exists", which
requires a live backend, so a reviewer without cluster access skipped it — though
it is checkable from the scrape config alone. Now its own section, ordered first.

*Four checks that did not exist.* A `up{job="..."}` panel, so a lost scrape target
is distinguishable from an idle service. Comparison against sibling dashboards in
the same repository — where the highest-value findings came from, and which no
single-file rule can see. Reading panel descriptions before judging a query, the
root cause of most false findings; in a mature repository the reasoning sits next
to the query and is newer than `docs/`. And rubric §4 now checks whether a
Prometheus-operator resource is **rendered**, not whether a template file exists —
a chart shipping `templates/servicemonitor.yaml` with `enabled: false` is correct.

Eleven tests now fail if any of these regress, including one that rejects the
old rate-window phrasing anywhere in the core skills.

## upstream-0.1.0-onprem.2

**generic-skill** — `observability-review` now states **where** its reports go, not
only what they contain. Every template said what to include and none said where to
save it, so each session invented a path and the reports became unfindable the
moment the session ended. Locations derive from the project profile's
`artifacts.root` (default `docs/superpowers`) rather than being hardcoded, and a
test now fails if a template omits its save location.

## upstream-0.1.0-onprem.1

**upstream-sync** — forked at upstream `d9dfb9ec7a6b1ac6c8ec9741ec045ad6f412dec6`,
recorded in `UPSTREAM_BASE`.

**security** — replaced `skill-review.yml` and `agent-scan.yml`, which authenticate
to Grafana's internal Vault for Tessl and Snyk tokens. A fork has no Vault role, so
both failed on every run. Replacements in `fork-config/workflows/` need no external
credentials, and `tests/test_public_workflows.py` fails if a Vault reference returns
or if an installed copy drifts from its canonical source.

**generic-skill** — added the `onprem-observability` plugin:

```text
observability-contract        the durable cross-project rules
application-instrumentation   capability-to-boundary decisions
log-pipeline                  stdout -> Alloy -> Loki OSS
metrics-pipeline              exporter -> scrape -> VictoriaMetrics
kubernetes-observability      VMServiceScrape, VMRule, dashboards, gateway
vm-docker-observability       Docker, Dokploy, systemd, bare metal
grafana-operations            datasources, dashboards-as-code, alert delivery
observability-review          evidence-based review
```

**generic-skill** — added the `onprem-observability-adapters` plugin: `scala-play`
and `rust`. Language adapters, not organization-wide assumptions.

**installer** — added `catalog/` as the single source of truth. One generator
writes all three marketplace manifests plus `skill-registry.json` and
`catalog/onprem-allowlist.json`. The upstream registry was incomplete — `grafana-core`
listed zero skills against eight declared, and `grafana-cloud` three against
nineteen — so nothing downstream could rely on it.

**security** — added `catalog/onprem-policy.yaml` and
`scripts/check-onprem-boundary.py`. Cloud paths, SaaS domains and publisher-role
literals cannot enter an on-prem distribution artifact. Upstream Cloud text stays
in the tree under `allow-text-but-forbid-cloud-execution`, so synchronization
remains mechanical.

**security** — added `scripts/scan-public-content.py`. No private project name,
internal hostname, RFC1918 address, credential or incident identifier may be
published here.

**installer** — added `scripts/check-upstream-boundary.py` and
`scripts/sync-upstream.py`. Upstream-owned paths are read-only; sync merges,
restores fork workflow overrides, regenerates catalogs and advances
`UPSTREAM_BASE` only after validation passes.

### Known deviations from the original plan

- The plan's Task 2 secret grep was scoped to fork-owned paths. Run verbatim over
  the whole tree it matches immutable upstream Cloud documentation and fails
  forever, which would make CI unusable rather than safe.
- The plan's `test_core_scope.py` listed private project identifiers as literals.
  Publishing those in a public repository is the leak this fork exists to prevent,
  so the public test is pattern-based and the exact-literal check lives in the
  private overlay, which already holds those names legitimately.
