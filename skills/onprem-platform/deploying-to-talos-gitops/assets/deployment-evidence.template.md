<!-- Save as: <artifacts.root>/evidence/YYYY-MM-DD-<release-slug>.md -->
# Deployment evidence — <release-slug>

> Evidence levels: `source-confirmed`, `runtime-evidence-supplied`,
> `runtime-reproduced`, `inference`, `not-verified`.

## 1. Scope and deployment layer

- Project/environment:
- Layer: workload | Talos machine config
- Approval and scope:
- Evidence level:

## 2. Release identity

| Identity | Value | Evidence level | Evidence source |
|---|---|---|---|
| `BUILD_VERSION` |  |  |  |
| `SOURCE_REVISION` |  |  |  |
| `IMAGE_DIGEST` |  |  |  |

## 3. Repositories and files

- Canonical source and revision:
- GitOps repository and target branch:
- Files reviewed:
- Landing order:

## 4. Validation evidence

| Check or command | Target/revision | Result | Evidence level |
|---|---|---|---|
|  |  |  |  |

## 5. Promotion or GitOps change

- Source and target environment:
- Same-digest promotion proof:
- Desired-state change and review:
- Reconciled revision:

## 6. Rollout evidence

- Controller reconciliation:
- Runtime image and Pod `imageID`:
- Readiness and rollout:
- Restarts, OOMs, and probe failures:
- Smoke test:
- Logs, metrics, and alerts:

## 7. Rollback point

- Previous verified digest and availability:
- Git rollback change:
- Migration constraints:
- Verification to repeat:

## 8. Risks and unverified items

| Item | Evidence level | Risk or consequence | Follow-up owner |
|---|---|---|---|
|  | `not-verified` |  |  |
