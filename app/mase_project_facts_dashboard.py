from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/mase_project_facts_summary.csv")
PROJECT_SUMMARY = Path("data/output/italy_project_summary.csv")
OUTPUT = Path("data/output/mase_project_facts_dashboard.csv")


# Valori principali selezionati dai candidati.
# Dove il dato è ancora dubbio, lo segnaliamo in quality_status / notes.
CURATED = {
    "10198": {
        "display_project": "Vantage MXP2",
        "primary_proponent": "VDC MXP 21 S.r.l.",
        "primary_developer": "Vantage Data Centers Europe",
        "primary_it_power_mw": "32",
        "primary_thermal_power_mwt": "143",
        "primary_site_area_m2": "",
        "quality_status": "ready",
        "notes": "MASE 10198 ricondotto a Vantage MXP2; scartati riferimenti di contesto a Equinix/Microsoft.",
    },
    "10745": {
        "display_project": "Equinix ML9",
        "primary_proponent": "EQUINIX HYPERSCALE 2 (ML9) S.r.l.",
        "primary_developer": "Equinix",
        "primary_it_power_mw": "",
        "primary_thermal_power_mwt": "108",
        "primary_site_area_m2": "",
        "quality_status": "ready",
        "notes": "ML9 isolato; ML7/ML8 e MXP2 sono riferimenti di contesto/cumulativi.",
    },
    "11965": {
        "display_project": "Equinix ML7-ML8",
        "primary_proponent": "EQUINIX HYPERSCALE 2 (ML7) S.r.l.",
        "primary_developer": "Equinix",
        "primary_it_power_mw": "",
        "primary_thermal_power_mwt": "133.6",
        "primary_site_area_m2": "",
        "quality_status": "ready",
        "notes": "Potenza aggiornata Proposta 2025: 133.6 MWt. Il valore 124.6 MWt si riferisce alla Proposta 2022; 150/50 MWt sono soglie normative.",
    },
    "8791": {
        "display_project": "Microsoft Bornasco",
        "primary_proponent": "MICROSOFT 4825 ITALY S.R.L.",
        "primary_developer": "Microsoft",
        "primary_it_power_mw": "",
        "primary_thermal_power_mwt": "163",
        "primary_site_area_m2": "165351",
        "quality_status": "ready",
        "notes": "Campus MIL05+MIL06; superficie e catasto coerenti con i candidati estratti.",
    },
}



def load_it_power_fallbacks() -> dict[str, dict[str, str]]:
    """Fallback controllato per MW IT da italy_project_summary.csv.

    Nota: questo NON è un dato estratto dai PDF MASE.
    Serve solo a evitare disallineamenti tra dashboard principale e pagina MASE facts.
    """
    if not PROJECT_SUMMARY.exists():
        return {}

    rows = read_rows(PROJECT_SUMMARY)
    out = {}

    for row in rows:
        project = (row.get("project") or "").strip().upper()
        developer = (row.get("developer") or "").strip()
        it_power = (row.get("it_power_mw") or "").strip()
        source_type = (row.get("source_type") or "").strip()
        source_url = (row.get("source_url") or "").strip()

        if not it_power:
            continue

        # Match sicuro: ML9 singolo, non ML7/ML8 aggregato.
        if project == "ML9":
            out["10745"] = {
                "it_power_mw": it_power,
                "source": source_type or "Italy Project Summary",
                "source_url": source_url,
                "note": f"MW IT da italy_project_summary.csv: {it_power} MW; non estratto dai PDF MASE.",
            }

    return out


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = read_rows(INPUT)
    it_power_fallbacks = load_it_power_fallbacks()
    output_rows = []

    for row in rows:
        object_id = row.get("mase_object_id", "").strip()
        curated = CURATED.get(object_id, {})

        display_project = curated.get("display_project") or row.get("project", "")
        primary_proponent = curated.get("primary_proponent") or row.get("primary_proponent", "")
        primary_developer = curated.get("primary_developer") or row.get("developer_hint", "")

        fallback = it_power_fallbacks.get(object_id, {})
        curated_it_power = curated.get("primary_it_power_mw", "")
        fallback_it_power = fallback.get("it_power_mw", "")
        primary_it_power = curated_it_power or fallback_it_power

        if curated_it_power:
            it_power_source = "MASE PDF"
        elif fallback_it_power:
            it_power_source = fallback.get("source", "Italy Project Summary")
        else:
            it_power_source = ""

        out = {
            "display_project": display_project,
            "source_project": row.get("project", ""),
            "developer_hint": row.get("developer_hint", ""),
            "primary_developer": primary_developer,
            "location": row.get("location", ""),
            "region": row.get("region", ""),
            "mase_object_id": object_id,
            "primary_proponent": primary_proponent,
            "campus_codes": row.get("campus_codes", ""),
            "primary_it_power_mw": primary_it_power,
            "primary_it_power_mw_source": it_power_source,
            "primary_it_power_mw_source_url": fallback.get("source_url", ""),
            "it_power_mw_candidates": row.get("it_power_mw_candidates", ""),
            "primary_thermal_power_mwt": curated.get("primary_thermal_power_mwt", ""),
            "thermal_power_mwt_candidates": row.get("thermal_power_mwt_candidates", ""),
            "primary_site_area_m2": curated.get("primary_site_area_m2", ""),
            "site_area_m2_candidates": row.get("site_area_m2_candidates", ""),
            "catasto": row.get("catasto", ""),
            "consultants": row.get("consultants", ""),
            "utilities": row.get("utilities", ""),
            "emails": row.get("emails", ""),
            "contact_persons": row.get("contact_persons", ""),
            "facts_total": row.get("facts_total", ""),
            "source_pdfs_count": row.get("source_pdfs_count", ""),
            "quality_status": curated.get("quality_status", "needs_review"),
            "notes": curated.get("notes", ""),
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

        output_rows.append(out)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "display_project",
        "source_project",
        "developer_hint",
        "primary_developer",
        "location",
        "region",
        "mase_object_id",
        "primary_proponent",
        "campus_codes",
        "primary_it_power_mw",
        "primary_it_power_mw_source",
        "primary_it_power_mw_source_url",
        "it_power_mw_candidates",
        "primary_thermal_power_mwt",
        "thermal_power_mwt_candidates",
        "primary_site_area_m2",
        "site_area_m2_candidates",
        "catasto",
        "consultants",
        "utilities",
        "emails",
        "contact_persons",
        "facts_total",
        "source_pdfs_count",
        "quality_status",
        "notes",
        "checked_at",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] Written {OUTPUT} with {len(output_rows)} dashboard rows")


if __name__ == "__main__":
    main()
