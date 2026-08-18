"""Reusable core skills must stay project- and runtime-neutral.

The exact private project identifiers are deliberately NOT listed here: writing
them into a public repository is the leak this fork exists to prevent. Detection
is pattern-based, and the private overlay runs the exact-literal check against a
checkout of this fork, where those names already legitimately live.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE = REPO_ROOT / "skills" / "onprem-observability"
ADAPTERS = REPO_ROOT / "skills" / "onprem-observability-adapters"
PLATFORM = REPO_ROOT / "skills" / "onprem-platform"

TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".sh", ".py"}

# Shapes that indicate a project-specific identifier leaked into a reusable skill.
#
# No concrete project name appears here on purpose: spelling one out in a public
# repository is the leak this fork exists to prevent. These patterns catch the
# *shape* of a repository slug being referenced as a concrete project. The exact
# private identifiers are checked by the private overlay's own core-scope test,
# which runs against a local checkout of this fork.
PROJECT_IDENTIFIER_PATTERNS = (
    # "the <slug> repository/service/project" — a core skill must stay generic and
    # say "the project profile" instead of naming one.
    (re.compile(r"(?i)\bthe\s+[a-z0-9]+(?:-[a-z0-9]+){1,3}\s+"
                r"(repository|repo|service|project|application)\b"),
     "concrete project reference"),
    # A git remote or clone URL pins a specific repository.
    (re.compile(r"(?i)(git@|https://)[a-z0-9.\-]+[:/][a-z0-9._\-]+/[a-z0-9._\-]+\.git"),
     "repository URL"),
)

# Project-specific control flow must not be imposed on every project by a core skill.
PROJECT_CONTROL_FLOW_PATTERNS = (
    (re.compile(r"poll\s*(->|→)\s*insert\s*(->|→)\s*commit\s*(->|→)\s*seek-back"),
     "project-specific Kafka control flow"),
    (re.compile(r"(?i)\bseek-back\b"), "project-specific Kafka control flow"),
)

# A reusable core skill must not assume one language or one orchestrator.
# Naming them as an example or a branch is fine; requiring them is not.
MANDATORY_STACK_PATTERNS = (
    (re.compile(r"(?i)\b(all|every|each)\s+(project|service)s?\s+(must|should)\s+"
                r"(use|run|be)\s+(scala|play|akka|talos|kubernetes)"),
     "mandatory stack assumption"),
    (re.compile(r"(?i)\brequires? (scala|play framework|akka|talos)\b"),
     "mandatory stack assumption"),
)


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def _scan(root: Path, patterns) -> list[str]:
    findings = []
    for path in _iter_files(root):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for regex, label in patterns:
                match = regex.search(line)
                if match:
                    findings.append(f"{rel}:{lineno}: {label}: {match.group(0)}")
    return findings


def test_core_skills_contain_no_project_identifier() -> None:
    assert _scan(CORE, PROJECT_IDENTIFIER_PATTERNS) == []


def test_adapters_contain_no_project_identifier() -> None:
    assert _scan(ADAPTERS, PROJECT_IDENTIFIER_PATTERNS) == []


def test_platform_skills_contain_no_project_identifier() -> None:
    assert _scan(PLATFORM, PROJECT_IDENTIFIER_PATTERNS) == []


def test_core_skills_impose_no_project_control_flow() -> None:
    assert _scan(CORE, PROJECT_CONTROL_FLOW_PATTERNS) == []


def test_platform_skills_impose_no_project_control_flow() -> None:
    assert _scan(PLATFORM, PROJECT_CONTROL_FLOW_PATTERNS) == []


def test_core_skills_assume_no_mandatory_stack() -> None:
    assert _scan(CORE, MANDATORY_STACK_PATTERNS) == []


def test_platform_skills_assume_no_mandatory_stack() -> None:
    assert _scan(PLATFORM, MANDATORY_STACK_PATTERNS) == []


def test_core_skills_do_not_assume_kubernetes_everywhere() -> None:
    """Kubernetes resources belong to the Kubernetes skill, not to shared core."""
    kubernetes_only = re.compile(r"\b(VMServiceScrape|VMRule|VMPodScrape)\b")
    allowed = {
        "skills/onprem-observability/kubernetes-observability",
        # The contract and the router-facing skills may name these to say when
        # they do NOT apply; those files are listed explicitly.
        "skills/onprem-observability/observability-contract/references/skill-routing.md",
        "skills/onprem-observability/observability-contract/references/rollout-and-evidence.md",
        "skills/onprem-observability/metrics-pipeline",
        "skills/onprem-observability/observability-review",
        "skills/onprem-observability/grafana-operations",
        # Names them only to forbid generating them outside Kubernetes.
        "skills/onprem-observability/vm-docker-observability",
    }
    findings = []
    for path in _iter_files(CORE):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(rel.startswith(prefix) for prefix in allowed):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if kubernetes_only.search(line):
                findings.append(f"{rel}:{lineno}: Kubernetes resource in a shared skill")
    assert findings == []


def test_every_core_skill_declares_onprem_compatibility() -> None:
    for skill_md in (
        sorted(CORE.glob("*/SKILL.md"))
        + sorted(ADAPTERS.glob("*/SKILL.md"))
        + sorted(PLATFORM.glob("*/SKILL.md"))
    ):
        head = skill_md.read_text(encoding="utf-8")[:2000]
        assert "compatibility:" in head, skill_md
        assert "no Grafana Cloud" in head, skill_md


# --- artifact locations ---------------------------------------------------
#
# A template that says what to write but not where to write it forces every
# session to invent a path. Six months on, nobody can find the review of a given
# service. The location is part of the contract.

ARTIFACT_TEMPLATES = {
    "skills/onprem-observability/observability-review/assets/review-report.template.md": "reviews",
    "skills/onprem-observability/observability-review/assets/validation-matrix.template.md": "validation",
    "skills/onprem-platform/deploying-to-talos-gitops/assets/deployment-evidence.template.md": "evidence",
}


def test_every_template_states_where_it_is_saved() -> None:
    for relative, folder in ARTIFACT_TEMPLATES.items():
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "Save as:" in text, f"{relative}: no save location"
        assert f"/{folder}/" in text, f"{relative}: wrong folder, expected {folder}"
        assert "artifacts.root" in text, f"{relative}: does not reference artifacts.root"


def test_review_skill_documents_the_artifact_root() -> None:
    skill = REPO_ROOT / "skills/onprem-observability/observability-review/SKILL.md"
    text = skill.read_text(encoding="utf-8")
    assert "artifacts.root" in text
    assert "docs/superpowers" in text


def test_output_contract_makes_the_location_binding() -> None:
    contract = (
        REPO_ROOT
        / "skills/onprem-observability/observability-review/references/output-contract.md"
    ).read_text(encoding="utf-8")
    assert "Where the file goes" in contract
    assert "artifacts.root" in contract


def test_templates_do_not_hardcode_a_repository_specific_path() -> None:
    """The default is a default, not a rule — a project may override the root."""
    for relative in ARTIFACT_TEMPLATES:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "<artifacts.root>" in text, f"{relative}: hardcodes a path"


# --- deployment counterpart and output contract --------------------------

KUBERNETES_OBSERVABILITY_SKILL = (
    REPO_ROOT / "skills/onprem-observability/kubernetes-observability/SKILL.md"
)
TALOS_GITOPS_SKILL = REPO_ROOT / "skills/onprem-platform/deploying-to-talos-gitops/SKILL.md"


def _description(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8")
    return text.split("---", 2)[1]


def test_kubernetes_observability_description_names_its_deployment_counterpart() -> None:
    assert "deploying-to-talos-gitops" in _description(KUBERNETES_OBSERVABILITY_SKILL)


def test_talos_gitops_description_names_its_observability_counterpart() -> None:
    assert "kubernetes-observability" in _description(TALOS_GITOPS_SKILL)


def test_talos_gitops_skill_has_complete_release_evidence_output_contract() -> None:
    text = TALOS_GITOPS_SKILL.read_text(encoding="utf-8")
    for heading in (
        "Scope and deployment layer",
        "Release identity",
        "Repositories and files",
        "Validation evidence",
        "Promotion or GitOps change",
        "Rollout evidence",
        "Rollback point",
        "Risks and unverified items",
    ):
        assert heading in text
    for identity in ("BUILD_VERSION", "SOURCE_REVISION", "IMAGE_DIGEST"):
        assert identity in text
    for evidence_level in (
        "source-confirmed",
        "runtime-evidence-supplied",
        "runtime-reproduced",
        "inference",
        "not-verified",
    ):
        assert evidence_level in text


# --- dashboard review checklist -------------------------------------------
#
# Each assertion below corresponds to a defect found by running the checklist
# against three real dashboards. The worst was a line that ticked PASS for the
# exact case it existed to catch.

CHECKLIST = (
    "skills/onprem-observability/kubernetes-observability/assets/"
    "dashboard-review-checklist.md"
)
RUBRIC = "skills/onprem-observability/observability-review/references/review-rubric.md"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_no_skill_states_the_useless_rate_window_rule() -> None:
    """"at least 4x the scrape interval" is satisfied by $__rate_interval by
    definition, so it passes over increase(...[$__interval]) — the real defect."""
    offenders = []
    for path in _iter_files(CORE):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "4x the scrape" not in line:
                continue
            # Naming the bad rule in order to reject it is allowed.
            window = "\n".join(text.splitlines()[max(0, lineno - 4):lineno + 3])
            # \s+ because the disclaimer may wrap across lines.
            if not re.search(r"(?i)\b(NOT\s+a\s+usable\s+check|Do\s+not\s+check)\b", window):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert offenders == []


def test_checklist_requires_rate_interval_and_datasource_floor() -> None:
    text = _read(CHECKLIST)
    assert "$__rate_interval" in text
    assert "jsonData.timeInterval" in text
    assert "increase(...[$__interval])" in text


def test_checklist_distinguishes_rate_panels_from_resource_panels() -> None:
    text = _read(CHECKLIST)
    assert "DO split by pod" in text
    assert "sum without (instance, pod)" in text


def test_checklist_exempts_histogram_mean_and_unitless_panels() -> None:
    text = _read(CHECKLIST)
    assert "sum(rate(x_sum)) / sum(rate(x_count))" in text
    assert "build_info" in text


def test_checklist_has_a_target_health_section() -> None:
    text = _read(CHECKLIST)
    assert 'up{job="..."}' in text
    assert "no traffic" in text


def test_checklist_requires_sibling_comparison() -> None:
    text = _read(CHECKLIST)
    assert "sibling dashboards" in text.lower()


def test_checklist_requires_reading_descriptions_first() -> None:
    text = _read(CHECKLIST)
    head = text.split("## 1.")[0]
    assert "description" in head.lower(), "must come before the judging sections"
    assert "NEWER" in head or "newer" in head


def test_checklist_separates_source_checkable_from_backend_checkable() -> None:
    text = _read(CHECKLIST)
    assert "Metric provenance" in text
    assert "checkable from source" in text.lower()
    assert "needs the real backend" in text.lower()


def test_checklist_requires_a_source_for_every_generated_artifact() -> None:
    assert "generated artifact with no source" in _read(CHECKLIST).lower()


def test_rubric_checks_rendered_resources_not_template_files() -> None:
    text = _read(RUBRIC)
    assert "RENDERED" in text
    assert "enabled: false is correct" in text


def test_rubric_dashboard_section_covers_the_new_checks() -> None:
    section = _read(RUBRIC).split("## 7. Dashboards")[1].split("## 8.")[0]
    for required in ('up{job="..."}', "sibling dashboards", "$__rate_interval",
                     "descriptions were read", "DO split by pod"):
        assert required in section, required


# --- §4 resolution vs span ------------------------------------------------
#
# The v0.3.0 wording caught the real defect but demanded that semantic spans be
# justified against the scrape interval — the wrong axis. Measured against three
# real dashboards: 14 literal windows, 12 already declaring their span in the
# panel title. These tests keep the two concepts apart.

def test_no_skill_judges_a_semantic_span_against_the_scrape_interval() -> None:
    offenders = []
    for path in _iter_files(CORE):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "justified against the scrape interval" not in line:
                continue
            window = "\n".join(text.splitlines()[max(0, lineno - 3):lineno + 2])
            if not re.search(r"(?i)\b(Do not ask|not judged against)\b", window):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert offenders == []


def test_checklist_separates_resolution_from_span() -> None:
    text = _read(CHECKLIST)
    assert "**Resolution**" in text
    assert "**Span**" in text
    assert "the panel TITLE" in text
    assert "Do not ask a semantic span" in text


def test_checklist_makes_the_interval_rule_greppable() -> None:
    """A reviewer should not have to infer whether $__interval is a defect."""
    text = _read(CHECKLIST)
    assert "$__interval on a Prometheus counter is a finding" in text
    assert "in a Loki query `$__interval` is the step" in text


def test_checklist_description_rule_produces_findings_not_only_suppression() -> None:
    text = _read(CHECKLIST)
    assert "states the panel's PURPOSE" in text
    assert "in every case, not only the common one" in text


def test_checklist_requires_anchored_metric_name_matching() -> None:
    text = _read(CHECKLIST)
    assert "full and anchored" in text
    assert "component_up{" in text


def test_checklist_requires_reproducibility_not_only_provenance() -> None:
    text = _read(CHECKLIST)
    assert "A note alone is not enough" in text
    assert "regenerated in this environment" in text


def test_rubric_mirrors_the_resolution_span_split() -> None:
    section = _read(RUBRIC).split("## 7. Dashboards")[1].split("## 8.")[0]
    assert "resolution:" in section
    assert "span:" in section
    assert "the panel TITLE counts" in section
    assert "in Loki it is the step" in section
