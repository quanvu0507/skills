# Upstream synchronization

The fork tracks `grafana/skills` by merging, never by rebasing or squashing. That
keeps the fork network intact and keeps the fork delta reviewable as a small set
of allowlisted paths.

## The allowed delta

`scripts/check-upstream-boundary.py` compares `UPSTREAM_BASE..HEAD` and fails if
anything under `skills/grafana-*` changed outside the allowlist:

```text
skills/onprem-observability/**
skills/onprem-observability-adapters/**
catalog/**
fork-config/**
scripts/**
tests/**
docs/**
generated marketplace and registry files
explicit workflow replacements
UPSTREAM_BASE
CHANGELOG-ONPREM.md
```

Run it locally before opening a PR:

```bash
python scripts/check-upstream-boundary.py \
  --base "$(cat UPSTREAM_BASE)" \
  --head HEAD
```

| Exit | Meaning |
|---:|---|
| 0 | only allowed delta |
| 1 | an upstream-owned path was modified |
| 2 | invalid configuration or baseline |

## Running a sync

```bash
python scripts/sync-upstream.py --upstream-ref upstream/main
```

The tool refuses to start on a dirty working tree, then:

1. fetches upstream;
2. creates `sync/upstream-<YYYYMMDD>-<short12>` — deterministic for a given
   upstream commit and day, so a re-run does not scatter branches;
3. merges `upstream/main` with a merge commit;
4. restores the fork workflow overrides from `fork-config/workflows/` and deletes
   any Vault-dependent workflow upstream reintroduced;
5. regenerates the catalogs;
6. runs lint, unit tests, catalog check, catalog validation and the on-prem
   boundary checker;
7. **advances `UPSTREAM_BASE` only after validation passes**;
8. pushes only when `--push` is given.

A merge conflict exits 2 and leaves the branch in place for manual resolution.
Failed validation exits 1 and leaves `UPSTREAM_BASE` at its last known-good value,
so the sync can be repeated after a fix without losing the baseline.

## Automation

`.github/workflows/upstream-sync.yml` runs weekly and on demand. It opens a
**draft** PR and uploads the validation log as an artifact. It never auto-merges,
and it never upgrades a consumer repository — consumers move only when someone
regenerates and commits a new `agent-skills/lock.json`.

## After a sync

1. Review the merge for upstream changes to skills used by on-prem selections.
2. Confirm the three marketplace manifests are still byte-identical.
3. Run the private overlay's benchmark before publishing a new lock.
4. Record the change in `CHANGELOG-ONPREM.md` under the `upstream-sync` class.
