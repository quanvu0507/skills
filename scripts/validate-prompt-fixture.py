#!/usr/bin/env python3
"""Validate prompt fixtures used for skill routing and regression tests.

Two fixture kinds share this validator:

  skill fixtures        positive/negative prompts for one skill
  capability-routing    expected and forbidden skills per environment+capability

A fixture that references a skill which does not exist, or that expects and
forbids the same skill, would silently pass a benchmark. This catches that before
the benchmark runs.

Exit codes:
    0  valid
    1  invalid fixture
    2  unreadable file
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
# Environments the fixtures may reference, and the runtime skill each implies.
ENVIRONMENT_RUNTIME_SKILL = {
    "kubernetes-talos": "kubernetes-observability",
    "docker-dokploy": "vm-docker-observability",
    "vm-systemd": "vm-docker-observability",
    "bare-metal": "vm-docker-observability",
    "desktop-local": None,
}


def custom_skill_groups(root: Path) -> tuple[str, ...]:
    payload = json.loads(
        (root / "catalog/onprem-plugins.json").read_text(encoding="utf-8")
    )
    return tuple(plugin["name"] for plugin in payload["plugins"])


def known_skills(root: Path) -> set[str]:
    return {
        skill_md.parent.name
        for group in custom_skill_groups(root)
        for skill_md in (root / "skills" / group).glob("*/SKILL.md")
    }


def _validate_skill_fixture(data: dict, skills: set[str], name: str) -> list[str]:
    errors = []
    skill = data.get("skill")
    if not skill:
        errors.append(f"{name}: missing 'skill'")
    elif skill not in skills:
        errors.append(f"{name}: unknown skill {skill!r}")

    path = data.get("path")
    if path and not (REPO_ROOT / path / "SKILL.md").is_file():
        errors.append(f"{name}: path has no SKILL.md: {path}")

    if not data.get("positive"):
        errors.append(f"{name}: needs at least one positive prompt")
    if not data.get("negative"):
        errors.append(f"{name}: needs at least one negative prompt")

    seen: set[str] = set()
    for section in ("positive", "negative"):
        for case in data.get(section) or []:
            case_id = case.get("id")
            if not case_id:
                errors.append(f"{name}: a {section} case has no id")
                continue
            if case_id in seen:
                errors.append(f"{name}: duplicate case id {case_id!r}")
            seen.add(case_id)
            if not case.get("prompt"):
                errors.append(f"{name}:{case_id}: missing prompt")
            if section == "negative" and not case.get("reason"):
                errors.append(f"{name}:{case_id}: negative case needs a reason")
            for key in ("expected_skills", "forbidden_skills"):
                for referenced in case.get(key) or []:
                    if referenced not in skills:
                        errors.append(
                            f"{name}:{case_id}: {key} references unknown skill "
                            f"{referenced!r}"
                        )
    return errors


def _validate_routing_fixture(data: dict, skills: set[str], name: str) -> list[str]:
    errors = []
    cases = data.get("cases") or []
    if not cases:
        errors.append(f"{name}: no cases")

    seen: set[str] = set()
    for case in cases:
        case_id = case.get("id", "<no id>")
        if case_id in seen:
            errors.append(f"{name}: duplicate case id {case_id!r}")
        seen.add(case_id)

        environment = case.get("environment")
        if environment not in ENVIRONMENT_RUNTIME_SKILL:
            errors.append(f"{name}:{case_id}: unknown environment {environment!r}")
        if not case.get("capabilities"):
            errors.append(f"{name}:{case_id}: no capabilities declared")

        expected = set(case.get("expected_skills") or [])
        forbidden = set(case.get("forbidden_skills") or [])
        if not expected:
            errors.append(f"{name}:{case_id}: no expected_skills")
        for referenced in expected | forbidden:
            if referenced not in skills:
                errors.append(
                    f"{name}:{case_id}: references unknown skill {referenced!r}"
                )
        overlap = expected & forbidden
        if overlap:
            errors.append(
                f"{name}:{case_id}: skill is both expected and forbidden: "
                f"{sorted(overlap)}"
            )

        # The runtime skill must follow the environment, never the language.
        runtime = ENVIRONMENT_RUNTIME_SKILL.get(environment)
        # A project that does not require metrics takes no collection skill.
        metrics_required = (case.get("observability") or {}).get("metrics", "required")
        if runtime and metrics_required == "disabled":
            runtime = None
        if runtime and runtime not in expected:
            errors.append(
                f"{name}:{case_id}: environment {environment} requires {runtime}"
            )
        for other_env, other_runtime in ENVIRONMENT_RUNTIME_SKILL.items():
            if other_env == environment or not other_runtime or other_runtime == runtime:
                continue
            if other_runtime in expected:
                errors.append(
                    f"{name}:{case_id}: {other_runtime} does not belong to "
                    f"environment {environment}"
                )
        if runtime is None and (expected & {"kubernetes-observability",
                                            "vm-docker-observability"}):
            errors.append(
                f"{name}:{case_id}: environment {environment} has no central scrape, "
                f"so it takes no runtime collection skill"
            )
    return errors


def validate(paths: list[Path]) -> list[str]:
    skills = known_skills(REPO_ROOT)
    errors: list[str] = []
    for path in paths:
        name = path.name
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{name}: cannot parse: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{name}: fixture is not a mapping")
            continue
        if data.get("kind") == "capability-routing":
            errors.extend(_validate_routing_fixture(data, skills, name))
        else:
            errors.extend(_validate_skill_fixture(data, skills, name))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", nargs="+", help="fixture files to validate")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.fixtures]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        for path in missing:
            print(f"error: no such fixture: {path}", file=sys.stderr)
        return 2

    errors = validate(paths)
    if errors:
        print("Prompt fixture validation failed:")
        for error in errors:
            print(f"  {error}")
        return 1

    print(f"validate-prompt-fixture: {len(paths)} fixture(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
