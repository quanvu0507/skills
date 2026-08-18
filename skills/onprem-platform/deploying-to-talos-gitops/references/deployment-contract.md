# Deployment contract and workload delivery

Use this reference for Kubernetes workload delivery, promotion, rollback, drift,
controller policy, migrations, and secrets. The project contract supplies values;
this public reference defines their meaning only.

## Contract resolution

Resolve the first complete contract from either the host's router/profile layer
or a user-supplied in-session contract. Echo an in-session contract and obtain
confirmation before use. If either project identity or a required key is absent,
list the absent `deployment.*` keys and stop. Do not derive missing values.

| Key | Required meaning |
|---|---|
| `deployment.source.canonical_remote` | Remote on which review and landing occur |
| `deployment.source.mirror_remotes` | Read-only mirrors that are not review targets |
| `deployment.gitops.repository` | Repository owning desired state |
| `deployment.gitops.target_branch` | Branch reconciled by the controller |
| `deployment.registry.endpoint` | Registry serving the immutable digest |
| `deployment.clusters` | Explicit environment-to-cluster mapping |
| `deployment.argocd.root_application` | Root Application and AppProject ownership |
| `deployment.argocd.child_policy` | Child self-heal, prune, and drift expectations |
| `deployment.approval` | Required approvers and approval locations |
| `deployment.validation.commands` | Render, schema, policy, and consistency checks |
| `deployment.machine_config` | Separate render, diff, approval, apply, verify rules |
| `deployment.rollback` | Git rollback and migration policy |
| `deployment.secrets.mechanism` | Supported secret delivery mechanism |
| `deployment.secrets.forbidden_paths` | Generated or secret-bearing paths never edited |

## Immutable release flow

1. Resolve the canonical source and full source revision.
2. Verify tests and the build for exactly that revision.
3. Resolve the built OCI artifact to a `sha256` digest in the target registry.
4. Record `BUILD_VERSION`, full `SOURCE_REVISION`, and `IMAGE_DIGEST` separately.
5. Promote the same digest to each environment; do not rebuild it.
6. Change only the GitOps desired-state source on its configured target branch.
7. Render desired state and run every applicable contract validation command.
8. Review the actual rendered image field and policy diff, then merge through the
   canonical remote.
9. Observe controller reconciliation and collect runtime evidence.

A tag is a lookup convenience, not immutable identity. A digest written in a
comment is not operative pinning. A short revision embedded in a tag is not full
provenance. When the original artifact is unavailable, stop promotion: rebuilding
creates a different artifact and requires a new release identity and validation.

## Desired-state validation

Run every applicable command in `deployment.validation.commands`, including the
project's equivalents of:

- Helm lint/template or Kustomize build;
- values/schema and Kubernetes manifest validation;
- operative immutable-image enforcement;
- plaintext-secret scanning;
- generated-artifact consistency checks;
- rendered desired-state diff review;
- migration ordering and compatibility checks.

Record command, source revision, result, and relevant output. Mark unavailable or
inapplicable checks explicitly; an unavailable check is `not-verified`, never a
pass. If application and GitOps repositories both change, state and enforce their
landing order.

## Migrations

Before promotion, specify application/schema order, backward/forward
compatibility, the migration executor, completion evidence, and rollback limits.
Prefer expand-migrate-contract sequencing. Do not assume a compatible-looking
schema makes ordering unnecessary, and do not claim application rollback can
undo an irreversible database change.

## Controller policy and drift

Inspect the effective child Application and its AppProject. Do not infer child
`selfHeal`, `prune`, sync options, destination permission, or drift behavior from
the root Application. Compare desired revision, rendered desired state, and live
state. Report unexplained drift before proceeding. Never enable self-heal or prune
unless the contract and a reviewed Git change explicitly authorize it.

## Secrets

Use only `deployment.secrets.mechanism`. Never place plaintext credentials in
values, manifests, evidence, logs, shell history, or Git. Never edit or disclose a
path in `deployment.secrets.forbidden_paths`. Validate ciphertext or external
reference structure without printing secret values. An ad hoc direct Secret
creation bypasses the Git-only deployment interface and is not a normal fix.

## Break glass and rollback

Normal deployment and rollback change Git, not live resources. Break glass
requires all four items: a contract-defined procedure, explicit human approval,
an audit record, and a plan to reconcile live state back to Git. Without all four,
stop.

For rollback, confirm the previous digest remains available, confirm its recorded
runtime evidence, account for migration compatibility, and propose a Git revert
or promotion change. Then repeat controller and runtime verification. Direct
resource rollback is not the official rollback record.
