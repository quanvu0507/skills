# ADR: Two-layer fork model for on-premises observability skills

**Status:** Accepted
**Deployment model:** `onprem` (fixed)

## Context

Every project in this organization runs its observability stack inside the internal
network: Grafana OSS for visualization, VictoriaMetrics for metrics, Loki OSS for
logs and Alloy for collection. The upstream `grafana/skills` repository is a
generic catalog that mixes OSS and Grafana Cloud guidance, and its CI depends on
Grafana-internal Vault roles that a fork cannot obtain.

We need reusable agent skills that encode on-premises observability constraints,
without leaking internal repository names, endpoints, topology or incident detail
into a public repository, and without an agent ever recommending a SaaS data plane.

## Alternatives considered

**A. One public fork containing internal knowledge.** Rejected — it would publish
private repository names, topology and operational assumptions.

**B. Full private copy of upstream, no GitHub fork.** Kept only as a fallback. It
loses the fork relationship, makes upstream content indistinguishable from local
modifications and turns every sync into a large manual merge.

**C. Public thin fork plus private on-prem overlay.** Chosen.

## Decision

1. **The public fork contains only reusable, generic on-prem knowledge.**
   `quanvu0507/skills` keeps the upstream tree intact and adds the
   `skills/onprem-observability/**` plugin plus `skills/onprem-observability-adapters/**`
   language adapters. Nothing here names a project, an internal host or a person.

2. **The private overlay owns project identity.** `quanvu0507/onprem-project-skills`
   holds `project-observability-router`, environment profiles, project profiles,
   per-project selections, the installer and the on-prem runtime policy. Project
   names, ownership boundaries and internal contracts live only there.

3. **Transient project state is never stored in a skill.** Profiles record durable
   contracts only. Current branch, commit, deployment status, incident status and
   runtime values must be re-checked in every working session. A profile is never
   evidence of current deployment state.

4. **Consumers pin an exact commit through a lock file.** Each consumer repository
   owns `agent-skills/lock.json`, which pins the public-fork commit, the private
   overlay commit resolved from an immutable tag, the resolved skill list and a
   SHA-256 checksum for every installed file. No consumer auto-upgrades.

5. **Upstream-owned paths are not edited directly.** Everything under
   `skills/grafana-*` is read-only in this fork, except for an explicit allowlist
   backed by a test and a stated security or correctness reason. Modifications are
   blocked by `scripts/check-upstream-boundary.py` in CI.

## On-premises boundary

`skills/grafana-cloud/**` may remain in the Git tree so `sync-upstream.py` keeps
working, but it is non-distributable source material: it never enters the on-prem
plugin catalog, a project selection, a consumer lock or an installed skill tree.
The private on-prem runtime contract takes precedence over any Cloud branch found
in an otherwise-allowed mixed upstream skill.

## Consequences

- Two repositories and one installer/lock mechanism must be maintained.
- Upstream sync stays mechanical because the fork delta is confined to an
  explicitly allowlisted set of paths.
- Generic improvements remain eligible for contribution back to upstream; private
  profiles never are.
