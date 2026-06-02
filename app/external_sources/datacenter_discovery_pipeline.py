from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "reports" / "external_sources"


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    module: str
    args: tuple[str, ...] = ()


STEPS: list[Step] = [
    Step(
        key="external_facts_review_export",
        label="External facts review export",
        module="app.external_sources.external_facts_review_export",
    ),
    Step(
        key="regional_environmental_probe",
        label="Regional environmental probe",
        module="app.external_sources.regional_environmental_probe",
    ),
    Step(
        key="regional_environmental_curator",
        label="Regional environmental curator",
        module="app.external_sources.regional_environmental_curator",
    ),
    Step(
        key="draft_external_enriched_report",
        label="Draft external enriched report",
        module="app.external_sources.draft_external_enriched_report",
    ),
    Step(
        key="datacentermap_probe",
        label="DataCenterMap probe",
        module="app.external_sources.datacentermap_probe",
    ),
    Step(
        key="datacentermap_curator",
        label="DataCenterMap curator",
        module="app.external_sources.datacentermap_curator",
    ),
    Step(
        key="datacentermap_new_candidates_export",
        label="DataCenterMap new candidates export",
        module="app.external_sources.datacentermap_new_candidates_export",
    ),
    Step(
        key="datacentermap_validation_queue",
        label="DataCenterMap validation queue",
        module="app.external_sources.datacentermap_validation_queue",
    ),
    Step(
        key="datacentermap_validation_summary",
        label="DataCenterMap validation summary",
        module="app.external_sources.datacentermap_validation_summary",
    ),
    Step(
        key="datacentermap_promotion_draft",
        label="DataCenterMap promotion draft",
        module="app.external_sources.datacentermap_promotion_draft",
    ),
    Step(
        key="external_candidates_site",
        label="External candidates site page",
        module="app.external_sources.external_candidates_site",
    ),
    Step(
        key="generate_project_pages_unified",
        label="Unified project pages",
        module="app.external_sources.generate_project_pages_unified",
        args=("--apply",),
    ),
    Step(
        key="promote_external_candidates_to_homepage",
        label="Promote external candidates to homepage",
        module="app.external_sources.promote_external_candidates_to_homepage",
    ),
    Step(
        key="normalize_homepage_status_terms",
        label="Normalize homepage status terms",
        module="app.external_sources.normalize_homepage_status_terms",
    ),
]


PROBE_STEP_KEYS = {
    "external_facts_review_export",
    "regional_environmental_probe",
    "regional_environmental_curator",
    "draft_external_enriched_report",
    "datacentermap_probe",
    "datacentermap_curator",
    "datacentermap_new_candidates_export",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the consolidated Data Center Radar external discovery pipeline."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected steps without executing them.",
    )

    parser.add_argument(
        "--start-at",
        choices=[s.key for s in STEPS],
        help="Start execution from this step key.",
    )

    parser.add_argument(
        "--stop-after",
        choices=[s.key for s in STEPS],
        help="Stop execution after this step key.",
    )

    parser.add_argument(
        "--skip-probes",
        action="store_true",
        help="Skip discovery/probe steps and run validation, promotion and page generation only.",
    )

    return parser.parse_args()


def selected_steps(args: argparse.Namespace) -> list[Step]:
    steps = STEPS

    if args.skip_probes:
        steps = [s for s in steps if s.key not in PROBE_STEP_KEYS]

    if args.start_at:
        start_idx = next(i for i, s in enumerate(steps) if s.key == args.start_at)
        steps = steps[start_idx:]

    if args.stop_after:
        stop_idx = next(i for i, s in enumerate(steps) if s.key == args.stop_after)
        steps = steps[: stop_idx + 1]

    return steps


def run_step(step: Step, index: int, total: int, dry_run: bool) -> None:
    cmd = [sys.executable, "-m", step.module, *step.args]

    print()
    print(f"[{index}/{total}] {step.label}")
    print(" ".join(cmd))

    if dry_run:
        return

    subprocess.run(cmd, cwd=ROOT, check=True)


def write_run_log(steps: list[Step], status: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().isoformat(timespec="seconds")
    log_path = LOG_DIR / "datacenter_discovery_pipeline_latest.txt"

    lines = [
        "Data Center Radar - discovery pipeline",
        f"timestamp: {now}",
        f"status: {status}",
        "",
        "steps:",
    ]

    for i, step in enumerate(steps, 1):
        args = " ".join(step.args)
        lines.append(f"{i}. {step.key} | {step.module} {args}".rstrip())

    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    print(f"[OK] Run log written: {log_path}")


def main() -> None:
    args = parse_args()
    steps = selected_steps(args)

    if not steps:
        raise SystemExit("No pipeline steps selected.")

    print("=== DATA CENTER RADAR - DISCOVERY PIPELINE ===")
    print(f"Root: {ROOT}")
    print(f"Steps selected: {len(steps)}")

    status = "dry-run" if args.dry_run else "completed"

    try:
        for i, step in enumerate(steps, 1):
            run_step(step, i, len(steps), args.dry_run)

    except subprocess.CalledProcessError as exc:
        status = f"failed: {exc.returncode}"
        write_run_log(steps, status)
        print()
        print(f"[ERROR] Step failed with exit code {exc.returncode}: {exc.cmd}")
        raise SystemExit(exc.returncode)

    write_run_log(steps, status)

    print()
    print("Pipeline completed.")


if __name__ == "__main__":
    main()
