# Talos machine-config workflow

Treat Talos machine configuration as a separate deployment layer. Do not process
it as a Kubernetes workload or manifest change.

## Safe sequence

1. Resolve `deployment.machine_config` and the required project approval.
2. Edit only the committed patch or generator input declared as source.
3. Start from a clean source revision and run the contract's render procedure.
4. Review a secret-safe rendered diff and the exact target scope.
5. Obtain explicit human approval after the diff is available.
6. Apply only with the command, mode, ordering, and safety checks defined by the
   project contract.
7. Verify node state and cluster health using the contract's read-only checks.
8. Record the source revision, approval, apply evidence, health evidence, and
   rollback or recovery limits in the eight-section artifact.

If the contract, clean render, secret-safe diff, explicit approval, target, or
health checks are absent, list the missing items and stop before application.

## Source and generated-output boundary

Never use `_out`, rendered machine configs, `kubeconfig`, `talosconfig`, PKI, or
other generated or secret-bearing output as source. Never edit, commit, upload,
or quote their sensitive content. A generated file already being present does
not authorize editing it. Change the committed patch source and reproduce the
render.

Inspect diffs through the project contract's redaction-safe procedure. If a tool
would print secrets, stop and choose a contract-approved safe inspection method.
Do not invent an apply command, node selector, endpoint, maintenance mode,
sequence, or recovery procedure.

## Verification

Use only contract-declared checks. Record the applicable node configuration
version, node readiness, control-plane health, cluster membership, workload
continuity, and any staged-application result. Do not call the change successful
from command exit status alone. Unavailable checks remain `not-verified`.
