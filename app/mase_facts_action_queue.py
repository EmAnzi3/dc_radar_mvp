from __future__ import annotations

import csv
from pathlib import Path


CONFIDENCE = Path("data/output/mase_facts_confidence_report.csv")
DASHBOARD = Path("data/output/mase_project_facts_dashboard.csv")
TARGETS = Path("data/input/mase_targets.csv")
OUTPUT = Path("data/output/mase_facts_action_queue.csv")


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        clean(r.get("mase_object_id")): r
        for r in rows
        if clean(r.get("mase_object_id"))
    }


def missing_fields(row: dict[str, str]) -> list[str]:
    checks = {
        "developer": "primary_developer",
        "proponente": "primary_proponent",
        "MW IT": "primary_it_power_mw",
        "MWt": "primary_thermal_power_mwt",
        "superficie": "primary_site_area_m2",
    }

    missing = []

    for label, field in checks.items():
        if not clean(row.get(field)):
            missing.append(label)

    return missing


def classify_action(row: dict[str, str]) -> tuple[str, str, str]:
    grade = clean(row.get("confidence_grade"))
    status = clean(row.get("confidence_status"))
    missing = missing_fields(row)

    if grade == "A":
        return (
            "P3",
            "monitoring",
            "Scheda pronta: mantenere in monitoraggio e aggiornare se emergono nuovi documenti."
        )

    if status == "review_required":
        return (
            "P2",
            "verify_pdf_evidence",
            "Verificare su PDF il dato tecnico primario già individuato."
        )

    if status == "partial_facts":
        if "MW IT" in missing and "MWt" in missing:
            return (
                "P1",
                "find_power_data",
                "Mancano MW IT e MWt primario: cercare nei PDF principali e poi in fonti developer/commerciali."
            )

        if "MWt" in missing:
            return (
                "P2",
                "verify_thermal_power",
                "MWt non consolidato: verificare generatori/gruppi elettrogeni nei PDF tecnici."
            )

        if "MW IT" in missing:
            return (
                "P2",
                "find_it_power",
                "MW IT assente: cercare in fonti developer/commerciali, non sempre presente nei fascicoli MASE."
            )

        return (
            "P2",
            "complete_missing_fields",
            "Facts parziali: completare dati mancanti."
        )

    if status == "external_sources_needed":
        return (
            "P1",
            "local_and_commercial_sources",
            "MASE insufficiente: usare Comune/SUAP/Regione/Città Metropolitana e fonti developer-commerciali."
        )

    return (
        "P2",
        "manual_review",
        "Stato non classificato: revisione manuale necessaria."
    )


def sort_key(row: dict[str, str]) -> tuple[int, str]:
    priority_order = {
        "P1": 1,
        "P2": 2,
        "P3": 3,
    }

    grade_order = {
        "D": 1,
        "C": 2,
        "B": 3,
        "A": 4,
    }

    return (
        priority_order.get(row["action_priority"], 9),
        str(grade_order.get(row["confidence_grade"], 9)),
        row["display_project"].lower(),
    )


def main() -> None:
    confidence_rows = read_csv(CONFIDENCE)
    dashboard_by_id = by_id(read_csv(DASHBOARD))
    targets_by_id = by_id(read_csv(TARGETS))

    output_rows = []

    for row in confidence_rows:
        object_id = clean(row.get("mase_object_id"))
        dash = dashboard_by_id.get(object_id, {})
        target = targets_by_id.get(object_id, {})

        action_priority, action_type, next_action = classify_action(row)
        missing = missing_fields(row)

        output_rows.append({
            "action_priority": action_priority,
            "action_type": action_type,
            "confidence_grade": clean(row.get("confidence_grade")),
            "confidence_status": clean(row.get("confidence_status")),
            "display_project": clean(row.get("display_project")),
            "mase_object_id": object_id,
            "source_url": clean(target.get("source_url")),
            "location": clean(dash.get("location") or target.get("location")),
            "region": clean(dash.get("region") or target.get("region")),
            "primary_developer": clean(row.get("primary_developer")),
            "primary_proponent": clean(row.get("primary_proponent")),
            "campus_codes": clean(row.get("campus_codes")),
            "primary_it_power_mw": clean(row.get("primary_it_power_mw")),
            "primary_thermal_power_mwt": clean(row.get("primary_thermal_power_mwt")),
            "primary_site_area_m2": clean(row.get("primary_site_area_m2")),
            "missing_fields": " | ".join(missing),
            "source_pdfs_count": clean(row.get("source_pdfs_count")),
            "facts_total": clean(row.get("facts_total")),
            "next_action": next_action,
            "notes": clean(row.get("notes")),
        })

    output_rows = sorted(output_rows, key=sort_key)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "action_priority",
        "action_type",
        "confidence_grade",
        "confidence_status",
        "display_project",
        "mase_object_id",
        "source_url",
        "location",
        "region",
        "primary_developer",
        "primary_proponent",
        "campus_codes",
        "primary_it_power_mw",
        "primary_thermal_power_mwt",
        "primary_site_area_m2",
        "missing_fields",
        "source_pdfs_count",
        "facts_total",
        "next_action",
        "notes",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] Written {OUTPUT} with {len(output_rows)} rows")


if __name__ == "__main__":
    main()
