from __future__ import annotations

import csv
from pathlib import Path


INPUT = Path("data/output/mase_project_facts_dashboard.csv")
OUTPUT = Path("data/output/mase_facts_confidence_report.csv")


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def has_value(row: dict[str, str], field: str) -> bool:
    return bool(clean(row.get(field)))


def classify(row: dict[str, str]) -> tuple[str, str, str]:
    quality = clean(row.get("quality_status"))
    proponent = has_value(row, "primary_proponent")
    developer = has_value(row, "primary_developer")
    it_mw = has_value(row, "primary_it_power_mw")
    thermal_mwt = has_value(row, "primary_thermal_power_mwt")
    area = has_value(row, "primary_site_area_m2")
    source_pdfs = int(clean(row.get("source_pdfs_count")) or "0")
    facts_total = int(clean(row.get("facts_total")) or "0")

    missing = []

    if not developer:
        missing.append("developer")
    if not proponent:
        missing.append("proponente")
    if not it_mw:
        missing.append("MW IT")
    if not thermal_mwt:
        missing.append("MWt")
    if not area:
        missing.append("superficie")

    if quality == "ready":
        return (
            "A",
            "ready",
            "Scheda utilizzabile: identità e dato tecnico principale già consolidati."
        )

    if quality == "needs_external_sources":
        return (
            "D",
            "external_sources_needed",
            "MASE agganciato ma insufficiente: servono fonti locali/commerciali."
        )

    if quality == "needs_review":
        if proponent and developer and (thermal_mwt or it_mw):
            return (
                "B",
                "review_required",
                "Scheda buona ma da verificare su PDF prima di considerarla pronta."
            )

        if source_pdfs > 0 and facts_total > 0:
            return (
                "C",
                "partial_facts",
                "Facts estratti ma dati chiave incompleti: " + ", ".join(missing)
            )

        return (
            "D",
            "weak_facts",
            "Pochi dati utili nonostante aggancio MASE: " + ", ".join(missing)
        )

    return (
        "D",
        "unknown_quality",
        "Stato qualità non riconosciuto o incompleto."
    )


def main() -> None:
    rows = read_csv(INPUT)

    output = []

    for row in rows:
        confidence_grade, confidence_status, confidence_notes = classify(row)

        output.append({
            "confidence_grade": confidence_grade,
            "confidence_status": confidence_status,
            "display_project": clean(row.get("display_project")),
            "mase_object_id": clean(row.get("mase_object_id")),
            "quality_status": clean(row.get("quality_status")),
            "primary_developer": clean(row.get("primary_developer")),
            "primary_proponent": clean(row.get("primary_proponent")),
            "campus_codes": clean(row.get("campus_codes")),
            "primary_it_power_mw": clean(row.get("primary_it_power_mw")),
            "primary_thermal_power_mwt": clean(row.get("primary_thermal_power_mwt")),
            "primary_site_area_m2": clean(row.get("primary_site_area_m2")),
            "source_pdfs_count": clean(row.get("source_pdfs_count")),
            "facts_total": clean(row.get("facts_total")),
            "confidence_notes": confidence_notes,
            "notes": clean(row.get("notes")),
        })

    fieldnames = [
        "confidence_grade",
        "confidence_status",
        "display_project",
        "mase_object_id",
        "quality_status",
        "primary_developer",
        "primary_proponent",
        "campus_codes",
        "primary_it_power_mw",
        "primary_thermal_power_mwt",
        "primary_site_area_m2",
        "source_pdfs_count",
        "facts_total",
        "confidence_notes",
        "notes",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)

    print(f"[OK] Written {OUTPUT} with {len(output)} rows")


if __name__ == "__main__":
    main()
