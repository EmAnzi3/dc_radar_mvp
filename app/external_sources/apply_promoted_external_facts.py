from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


MASTER = Path("data/output/dc_project_fused_master.csv")
PROMOTED = Path("data/input/external_sources/promoted_external_facts.csv")
AUDIT = Path("data/output/external_sources/promoted_external_facts_audit.csv")

FIELD_ALIASES = {
    "thermal_power_mwt": "thermal_mwt",
    "primary_thermal_power_mwt": "thermal_mwt",
}


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
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_missing(value: object) -> bool:
    v = clean(value).lower()

    return v in {
        "",
        "-",
        "—",
        "n/a",
        "na",
        "none",
        "null",
        "nan",
        "da identificare",
        "da verificare",
        "non disponibile",
    }


def ensure_column(fieldnames: list[str], column: str) -> None:
    if column not in fieldnames:
        fieldnames.append(column)


def main() -> None:
    master_rows = read_csv(MASTER)
    promoted_rows = read_csv(PROMOTED)

    if not master_rows:
        raise SystemExit(f"Master non trovato o vuoto: {MASTER}")

    if not promoted_rows:
        raise SystemExit(f"Promoted facts non trovato o vuoto: {PROMOTED}")

    fieldnames = list(master_rows[0].keys())

    ensure_column(fieldnames, "external_promoted_fields")
    ensure_column(fieldnames, "external_promoted_sources")
    ensure_column(fieldnames, "external_promoted_updated_at")

    by_project = {clean(r.get("project")): r for r in master_rows}

    audit_rows: list[dict[str, str]] = []

    for p in promoted_rows:
        project = clean(p.get("project"))
        raw_target_field = clean(p.get("target_field"))
        target_field = FIELD_ALIASES.get(raw_target_field, raw_target_field)
        promoted_value = clean(p.get("promoted_value"))

        if not project or not target_field or not promoted_value:
            audit_rows.append({
                "project": project,
                "target_field": target_field,
                "old_value": "",
                "new_value": promoted_value,
                "status": "skipped_invalid_row",
                "source_label": clean(p.get("source_label")),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        row = by_project.get(project)

        if not row:
            audit_rows.append({
                "project": project,
                "target_field": target_field,
                "old_value": "",
                "new_value": promoted_value,
                "status": "skipped_project_not_found",
                "source_label": clean(p.get("source_label")),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        ensure_column(fieldnames, target_field)

        old_value = clean(row.get(target_field))

        # Applichiamo solo se il campo è assente.
        # Se è già valorizzato, non lo sovrascriviamo a martellate.
        if not is_missing(old_value):
            audit_rows.append({
                "project": project,
                "target_field": target_field,
                "old_value": old_value,
                "new_value": promoted_value,
                "status": "skipped_existing_value",
                "source_label": clean(p.get("source_label")),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        row[target_field] = promoted_value

        promoted_fields = []
        for x in clean(row.get("external_promoted_fields")).split("|"):
            x = x.strip()
            if not x:
                continue
            x = FIELD_ALIASES.get(x, x)
            if x not in promoted_fields:
                promoted_fields.append(x)

        if target_field not in promoted_fields:
            promoted_fields.append(target_field)

        promoted_sources = [
            x.strip()
            for x in clean(row.get("external_promoted_sources")).split("|")
            if x.strip()
        ]
        source_label = clean(p.get("source_label"))
        if source_label and source_label not in promoted_sources:
            promoted_sources.append(source_label)

        row["external_promoted_fields"] = " | ".join(promoted_fields)
        row["external_promoted_sources"] = " | ".join(promoted_sources)
        row["external_promoted_updated_at"] = datetime.now().isoformat(timespec="seconds")

        audit_rows.append({
            "project": project,
            "target_field": target_field,
            "old_value": old_value,
            "new_value": promoted_value,
            "status": "applied",
            "source_label": source_label,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    normalized_rows = []

    for row in master_rows:
        normalized_rows.append({field: clean(row.get(field)) for field in fieldnames})

    write_csv(MASTER, normalized_rows, fieldnames)

    write_csv(
        AUDIT,
        audit_rows,
        [
            "project",
            "target_field",
            "old_value",
            "new_value",
            "status",
            "source_label",
            "checked_at",
        ],
    )

    applied = sum(1 for r in audit_rows if r["status"] == "applied")

    print(f"[OK] Applied promoted external facts: {applied}")
    print(f"[OK] Updated {MASTER}")
    print(f"[OK] Written {AUDIT}")


if __name__ == "__main__":
    main()
