# Verification evidence

Use this reference to distinguish source, controller, and runtime evidence and to
write the deployment evidence artifact.

## Evidence levels

Apply exactly one level to each claim:

| Level | Meaning |
|---|---|
| `source-confirmed` | Verified in committed source, rendered desired state, registry metadata, or reproducible build records |
| `runtime-evidence-supplied` | Current runtime evidence was supplied by a trusted operator or system but not reproduced in this session |
| `runtime-reproduced` | Read-only runtime inspection was executed and captured in this session |
| `inference` | A conclusion follows from evidence but was not directly observed; state the reasoning |
| `not-verified` | Evidence is unavailable, stale, failed, or not collected |

Never convert `inference` or `not-verified` into a success claim. Include command,
timestamp, target, and result when available, while redacting secrets.

## Controller evidence is not runtime evidence

Controller `Synced` and `Healthy` establish reconciliation state only. Capture the
reconciled Git revision, child Application state, AppProject relationship, and
effective child self-heal/prune policy. Then independently establish runtime
identity and health. Lack of cluster access leaves runtime claims `not-verified`.

## Runtime identity and health

Collect the applicable subset:

- rendered desired image reference and live workload image reference;
- Pod `imageID` or equivalent runtime digest, matched to `IMAGE_DIGEST`;
- observed generation, readiness, available replicas, and rollout status;
- container restart counts, OOM terminations, and readiness/liveness/startup
  probe failures;
- build/version endpoint or build-info metric tied to `BUILD_VERSION` and full
  `SOURCE_REVISION`;
- service-specific smoke test with expected outcome;
- relevant logs, metrics, dashboards, and alert regression gates.

Do not use an image tag alone as runtime identity. Record mismatches between
desired image, live image, and runtime `imageID` as a release blocker.

## Eight-section artifact schema

Write the evidence artifact beneath the project contract's `artifacts.root` and
include these sections in order:

1. **Scope and deployment layer** — project, environment, workload versus
   machine-config classification, approvals, and whether work is read-only or a
   proposed Git change.
2. **Release identity** — `BUILD_VERSION`, full `SOURCE_REVISION`, and
   `IMAGE_DIGEST`, each with evidence level and source.
3. **Repositories and files** — canonical source, GitOps repository, target
   branch, reviewed files, canonical review target, and multi-repository landing
   order.
4. **Validation evidence** — exact render, schema, policy, secret, consistency,
   migration, and diff checks with results.
5. **Promotion or GitOps change** — source/target environment, proof the same
   digest is reused, desired-state diff, review, and reconciliation revision.
6. **Rollout evidence** — controller evidence separated from runtime identity,
   readiness, restarts/OOM/probes, smoke tests, and logs/metrics/alerts.
7. **Rollback point** — previous verified digest, availability, Git rollback
   change, migration constraints, and evidence to repeat.
8. **Risks and unverified items** — every inference, unavailable check, stale
   observation, unresolved drift, missing approval, and follow-up owner.

Use `assets/deployment-evidence.template.md` as the writing scaffold. Never place
credentials or secret values in the artifact.
