# Upstream contributions

The fork stays small on purpose. Anything generically useful belongs upstream in
`grafana/skills`, where it is maintained by more people and cannot drift.

## Eligible for an upstream PR

```text
generic catalog validation
generic linter improvements
reusable Scala/Play observability content
generic evidence-based review improvements
fixes to upstream skills verified independently
```

A fix to an upstream skill is the strongest case: keeping it here means editing an
upstream-owned path, which the boundary checker blocks and which turns every future
sync into a manual merge.

## Never upstream

```text
private repository names
source topology
internal routes or endpoints
credentials or infrastructure access
current incident details
private handoff or evaluation data
```

If a change cannot be described without naming an internal system, it belongs in
the private overlay, not upstream and not in this fork.

## Before opening a PR

```text
[ ] the change is generic — it names no internal system and assumes no internal topology
[ ] it is verified independently of our environment
[ ] it carries a test
[ ] scripts/scan-public-content.py is clean on the diff
[ ] the fork's own copy is removed once upstream accepts it
```

That last line is what keeps the fork thin. A change accepted upstream and also
kept here becomes a conflict at the next sync.

## Modifying an upstream-owned path in the fork

Only with all three:

```text
1. a stated security or correctness reason
2. a test covering the change
3. an explicit entry in the allowlist in scripts/check-upstream-boundary.py
```

Record the reason in `CHANGELOG-ONPREM.md` under the `security` class, and open
the corresponding upstream PR so the local patch can be removed later.
