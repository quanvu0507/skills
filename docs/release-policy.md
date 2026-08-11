# Release policy — public fork

## Change classes

```text
upstream-sync
generic-skill
private-profile
trigger-breaking
security
installer
benchmark
```

Every entry in `CHANGELOG-ONPREM.md` carries one. `private-profile` should never
appear here — if it does, private content has reached the public fork.

## Versioning

Tags follow `upstream-<upstream-version>-onprem.<n>`.

| Change | Version effect |
|---|---|
| upstream-only sync, no custom behaviour change | increment the `onprem` patch suffix |
| skill trigger or output contract change | increment the custom minor |
| incompatible rename or removal | increment the custom major |

A trigger change is a breaking change even though nothing fails to compile: a
skill that stops auto-loading is silently absent, which is worse than an error.

`scripts/release.py` in the private overlay reads `.metadata.version` from the
upstream marketplace and increments the final `onprem.N` suffix.

## Tags are immutable

A tag is never moved. Consumer locks resolve commits from tags, so moving one
would change what an existing lock installs — content nobody reviewed, under a
version someone already approved.

## Sync cadence

```text
weekly automated draft sync PR
immediate sync for upstream security or correctness fixes affecting selected skills
full benchmark before releasing a new lock
no consumer repository auto-upgrade
```

`.github/workflows/upstream-sync.yml` opens a draft PR and uploads its validation
log. It never merges, and merging it changes nothing in any consumer until someone
regenerates and commits a lock.

## Release checklist

```text
[ ] ./scripts/lint-skills.sh skills
[ ] python -m pytest -q
[ ] python scripts/generate-catalog.py --check
[ ] python scripts/validate-catalog.py
[ ] python scripts/check-upstream-boundary.py --base "$(cat UPSTREAM_BASE)" --head HEAD
[ ] python scripts/check-onprem-boundary.py --policy catalog/onprem-policy.yaml \
      --marketplace .agents-plugin/marketplace.json --scan skills/onprem-observability
[ ] python scripts/scan-public-content.py
[ ] CHANGELOG-ONPREM.md entry with a change class
[ ] tag, and never move it
```
