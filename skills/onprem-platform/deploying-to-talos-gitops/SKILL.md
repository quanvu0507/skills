---
name: deploying-to-talos-gitops
license: Apache-2.0
compatibility: "Kubernetes and Talos environments managed through GitOps and OCI registries; works with project-supplied controllers and validation tools; no Grafana Cloud dependency"
description: "Use when planning, reviewing, promoting, deploying, rolling back, or verifying Kubernetes workloads or Talos machine configuration managed through GitOps. Use kubernetes-observability as the counterpart for scrape resources, alert rules, dashboards, gateway policy, and release observability."
user-invocable: true
disable-model-invocation: false
---

# Deploying to Talos GitOps

Preserve one auditable chain:

```text
source commit -> build once -> immutable OCI digest -> reviewed GitOps change
-> controller reconciliation -> runtime evidence -> Git-based rollback
```

## Decision order

Follow this order without skipping a gate:

1. Identify the target project and load its project contract.
2. Classify the request as a Kubernetes workload change or Talos machine-config change.
3. Validate every required `deployment.*` key and stop if the contract is incomplete.
4. Resolve `BUILD_VERSION`, full `SOURCE_REVISION`, and `IMAGE_DIGEST` as separate values.
5. Read the matching references before proposing a change.
6. Perform read-only validation, or propose a reviewed Git change and its landing order.
7. Emit the eight-section evidence report below.

Do not mutate a live cluster, GitOps controller, registry, or Talos node unless the
project contract explicitly defines the operation and the required approval has
been supplied. Read-only inspection is allowed.

## Resolve the project contract or stop

Resolve the named interface in this order; the first complete source wins:

1. A project contract supplied by the host router or profile layer.
2. A contract supplied in-session by the user. Echo it back and obtain
   confirmation before using it.

Require all of these keys:

```text
deployment.source.canonical_remote
deployment.source.mirror_remotes
deployment.gitops.repository
deployment.gitops.target_branch
deployment.registry.endpoint
deployment.clusters
deployment.argocd.root_application
deployment.argocd.child_policy
deployment.approval
deployment.validation.commands
deployment.machine_config
deployment.rollback
deployment.secrets.mechanism
deployment.secrets.forbidden_paths
```

If project identity or any required key is absent, print `Missing deployment
contract keys:` followed by the exact absent keys and stop. Never infer a
registry, branch, cluster, approver, canonical remote, child policy, secret
mechanism, or rollback point from names, URLs, directory layout, root policy, or
comments. Read [`references/deployment-contract.md`](references/deployment-contract.md)
for the contract semantics and workload workflow.

## Classify the deployment layer

- For a Kubernetes workload, preserve the build-once digest, propose only a
  desired-state Git change, run the contract's validation commands, and verify
  controller plus runtime state.
- For Talos machine config, edit committed patch source, render cleanly, review
  a secret-safe diff, require explicit approval, apply only through the contract,
  and verify node and cluster health. Read
  [`references/talos-machine-config.md`](references/talos-machine-config.md).
- For runtime claims and evidence levels, read
  [`references/verification-evidence.md`](references/verification-evidence.md).

## Release identity

Keep the tuple distinct and complete:

```text
BUILD_VERSION   = human-readable release or tag
SOURCE_REVISION = full Git commit that produced the artifact
IMAGE_DIGEST    = immutable OCI digest in sha256 form
```

`Chart.version`, `Chart.appVersion`, a tag, a short SHA in a tag, and a comment
containing a digest do not substitute for any tuple member. Build once from the
full source revision, record the resulting digest, and promote that same digest
through every environment. Never rebuild merely to promote.

## Normal workload and rollback interface

The official workload path is Git-only:

```text
resolve canonical source and full revision -> verify tests and build
-> resolve immutable digest -> reuse the digest for promotion
-> edit GitOps desired state -> render and validate -> review and merge
-> observe reconciliation -> verify runtime identity and service health
```

Do not use `kubectl apply`, `kubectl set image`, `kubectl rollout undo`, `helm
upgrade`, controller parameter overrides, or direct resource edits as the normal
deployment or rollback path. Roll back with a Git revert or a Git promotion
change to a previously verified digest after confirming that digest still
exists. Treat database migrations as a separately ordered compatibility and
rollback gate. A break-glass mutation is valid only when the contract defines
the procedure, a human explicitly approves it, an audit record is created, and
the resulting state is reconciled back to Git.

## Counterpart boundary

| Concern | Owner |
|---|---|
| Image identity, digest, promotion, rollout, rollback | `deploying-to-talos-gitops` |
| Talos machine configuration | `deploying-to-talos-gitops` |
| VMServiceScrape, VMRule, dashboards, gateway policy | `kubernetes-observability` |
| Whether a release is observable enough to verify | `kubernetes-observability` |
| Whether a release is verified | `deploying-to-talos-gitops` |

Load both skills when a change crosses the boundary; this skill owns the landing
order. Observability resources never establish artifact identity or deployment
completion.

## Pressure rationalizations and required response

| Unsafe shortcut or rationalization | Required response |
|---|---|
| An outage, deadline, or authority makes direct mutation faster | Keep Git as the official path; use break glass only when its full contract is satisfied. |
| A familiar or apparently immutable tag is good enough | Require the operative manifest to pin `IMAGE_DIGEST`. |
| Rebuilding the same source is equivalent to promotion | Promote the already-tested digest; a rebuild is a new artifact and release. |
| Controller `Synced` and `Healthy` prove completion | Report controller evidence only until runtime identity and health are verified. |
| Direct rollback restores service faster | Revert Git or promote a previously verified available digest. |
| Editing generated machine config can be reconciled later | Edit committed patch source and produce a clean render. |
| A temporary plaintext secret can be cleaned up later | Use only the contract's secret mechanism; never commit plaintext or bypass Git with an ad hoc secret. |
| Root Application policy implies child policy | Inspect the effective child Application and AppProject policy. |
| A digest in a comment makes a tagged manifest immutable | Verify the operative rendered and live image reference. |
| A short SHA in a tag proves provenance | Require the full `SOURCE_REVISION` and artifact evidence. |
| Compatible-looking migrations need no ordering | State application/schema order, compatibility window, and rollback limits. |
| A reachable mirror is sufficient for review | Review and land on `deployment.source.canonical_remote`; mirrors are not review targets. |

## Required evidence output

Write the report to
`<artifacts.root>/evidence/YYYY-MM-DD-<release-slug>.md` using
[`assets/deployment-evidence.template.md`](assets/deployment-evidence.template.md).
Return these sections in this exact order, even when a section contains only
`not-verified`:

1. **Scope and deployment layer**
2. **Release identity**
3. **Repositories and files**
4. **Validation evidence**
5. **Promotion or GitOps change**
6. **Rollout evidence**
7. **Rollback point**
8. **Risks and unverified items**

When application and GitOps repositories both change, state their landing order.
Label every claim `source-confirmed`, `runtime-evidence-supplied`,
`runtime-reproduced`, `inference`, or `not-verified`; never upgrade unavailable
evidence into success.
