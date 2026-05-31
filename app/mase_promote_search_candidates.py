from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from pathlib import Path


CANDIDATES = Path("data/output/mase_search_pages_data_center_candidates.csv")
TARGETS = Path("data/input/mase_targets.csv")
PROMOTED_OUT = Path("data/output/mase_promoted_targets_latest.csv")


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def infer_score(row: dict[str, str]) -> int:
    project = clean(row.get("project")).lower()
    procedure = clean(row.get("procedure")).lower()
    proponent = clean(row.get("proponent")).lower()
    priority = clean(row.get("priority"))

    score = 0

    if priority == "P1":
        score += 100
    elif priority == "P2":
        score += 70
    elif priority == "P3":
        score += 20

    if "valutazione impatto ambientale" in procedure:
        score += 30
    if "verifica di assoggettabilità" in procedure:
        score += 25
    if "verifica di ottemperanza" in procedure:
        score += 15

    strong_terms = [
        "microsoft",
        "equinix",
        "vantage",
        "data4",
        "data 4",
        "stack",
        "supernap",
        "aruba",
        "aws",
        "noovle",
        "digital realty",
        "cyrusone",
        "apto",
    ]

    for term in strong_terms:
        if term in project or term in proponent:
            score += 8

    if "generatori" in project or "gruppi elettrogeni" in project:
        score += 8
    if "mw" in project or "mwt" in project or "mwth" in project:
        score += 8

    # Penalizza record troppo generici o chiaramente appendici
    if "inserimento pozzi" in project:
        score -= 20
    if "definizione del livello di dettaglio" in project:
        score -= 10

    return score


def normalize_project_name(project: str) -> str:
    p = clean(project)

    replacements = [
        (r"^Progetto\s+", ""),
        (r"^Istanza per l'avvio del procedimento.*relativa al progetto\s+", ""),
        (r"\s+", " "),
    ]

    for pattern, repl in replacements:
        p = re.sub(pattern, repl, p, flags=re.IGNORECASE)

    return p.strip(" .")


def main() -> None:
    candidates = read_csv(CANDIDATES)
    targets = read_csv(TARGETS)

    if not candidates:
        raise FileNotFoundError(f"No candidates found in {CANDIDATES}")

    target_ids = {
        clean(r.get("mase_object_id"))
        for r in targets
        if clean(r.get("mase_object_id"))
    }

    eligible = []

    for row in candidates:
        object_id = clean(row.get("mase_object_id"))
        source_url = clean(row.get("source_url"))
        status = clean(row.get("candidate_status"))
        priority = clean(row.get("priority"))

        if not object_id or not source_url:
            continue

        if object_id in target_ids:
            continue

        if priority not in {"P1", "P2"}:
            continue

        if status not in {"new_mase_candidate", "maybe_already_in_dashboard"}:
            continue

        enriched = dict(row)
        enriched["_score"] = infer_score(row)
        eligible.append(enriched)

    eligible = sorted(
        eligible,
        key=lambda r: (
            -int(r["_score"]),
            clean(r.get("project")).lower(),
            clean(r.get("mase_object_id")),
        ),
    )

    limit_raw = os.environ.get("MASE_PROMOTE_LIMIT", "8").strip()
    limit = int(limit_raw) if limit_raw else 8

    if limit > 0:
        selected = eligible[:limit]
    else:
        selected = eligible

    now = datetime.now().isoformat(timespec="seconds")

    new_target_rows = []
    promoted_rows = []

    for row in selected:
        project = normalize_project_name(clean(row.get("project")))
        developer = clean(row.get("proponent"))
        location = clean(row.get("location_guess"))
        region = clean(row.get("region_guess"))
        object_id = clean(row.get("mase_object_id"))
        source_url = clean(row.get("source_url"))
        procedure = clean(row.get("procedure"))
        documentation_url = clean(row.get("documentation_url"))

        notes = (
            f"{procedure}; imported from MASE search pages; "
            f"documentation={documentation_url}; promoted_at={now}"
        )

        new_target_rows.append({
            "project": project,
            "developer": developer,
            "location": location,
            "region": region,
            "mase_object_id": object_id,
            "source_url": source_url,
            "notes": notes,
        })

        promoted_rows.append({
            "score": str(row["_score"]),
            "project": project,
            "developer": developer,
            "location": location,
            "region": region,
            "mase_object_id": object_id,
            "source_url": source_url,
            "documentation_url": documentation_url,
            "procedure": procedure,
            "candidate_status": clean(row.get("candidate_status")),
            "priority": clean(row.get("priority")),
            "dashboard_match": clean(row.get("dashboard_match")),
            "promoted_at": now,
        })

    # Normalizza anche eventuali target vecchi con header coerente
    normalized_targets = []
    for r in targets:
        normalized_targets.append({
            "project": clean(r.get("project")),
            "developer": clean(r.get("developer") or r.get("developer_hint")),
            "location": clean(r.get("location")),
            "region": clean(r.get("region")),
            "mase_object_id": clean(r.get("mase_object_id")),
            "source_url": clean(r.get("source_url") or r.get("mase_url")),
            "notes": clean(r.get("notes")),
        })

    all_targets = normalized_targets + new_target_rows

    fieldnames = [
        "project",
        "developer",
        "location",
        "region",
        "mase_object_id",
        "source_url",
        "notes",
    ]

    write_csv(TARGETS, all_targets, fieldnames)

    promoted_fields = [
        "score",
        "project",
        "developer",
        "location",
        "region",
        "mase_object_id",
        "source_url",
        "documentation_url",
        "procedure",
        "candidate_status",
        "priority",
        "dashboard_match",
        "promoted_at",
    ]

    write_csv(PROMOTED_OUT, promoted_rows, promoted_fields)

    print(f"[OK] Eligible candidates: {len(eligible)}")
    print(f"[OK] Promoted targets: {len(promoted_rows)}")
    print(f"[OK] Updated {TARGETS}")
    print(f"[OK] Written {PROMOTED_OUT}")


if __name__ == "__main__":
    main()
