from __future__ import annotations

import csv
from pathlib import Path


DASHBOARD = Path("data/output/mase_project_facts_dashboard.csv")
TARGETS = Path("data/input/mase_targets.csv")


CURATED = {
    "11218": {
        "display_project": "Noovle Data Center",
        "primary_developer": "Noovle SpA",
        "primary_proponent": "Noovle SpA",
        "campus_codes": "",
        "primary_thermal_power_mwt": "",
        "quality_status": "needs_review",
        "notes": "Facts MASE poveri; identità progetto/proponente normalizzata da target MASE. Da completare con fonti locali/commerciali.",
    },
    "11308": {
        "display_project": "Aruba Roma Tecnopolo Tiburtino",
        "primary_developer": "Aruba S.p.A.",
        "primary_proponent": "Aruba S.p.A.",
        "campus_codes": "",
        "primary_thermal_power_mwt": "50",
        "quality_status": "needs_review",
        "notes": "Proponente pulito da target MASE; potenza termica 50 MWt dai candidati estratti. Da verificare su documento PDF.",
    },
    "11503": {
        "display_project": "Apto Lacchiarella",
        "primary_developer": "APTO ITALIA S.R.L.",
        "primary_proponent": "APTO ITALIA S.R.L.",
        "campus_codes": "",
        "primary_thermal_power_mwt": "",
        "quality_status": "needs_review",
        "notes": "Molti candidati MWt e superfici estratti; non selezionato un valore primario per evitare dato fuorviante. Richiede verifica PDF.",
    },
    "11703": {
        "display_project": "Stack Campus Siziano",
        "primary_developer": "Infrastructure Italia Land 2 S.r.l.",
        "primary_proponent": "Infrastructure Italia Land 2 S.r.l.",
        "campus_codes": "",
        "primary_thermal_power_mwt": "",
        "quality_status": "needs_review",
        "notes": "Molti candidati MWt e superfici estratti; non selezionato un valore primario per evitare dato fuorviante. Richiede verifica PDF.",
    },
    "11794": {
        "display_project": "Equinix ML5-ML6",
        "primary_developer": "Equinix Italia S.r.l.",
        "primary_proponent": "Equinix Italia S.r.l.",
        "campus_codes": "ML5 | ML6",
        "primary_thermal_power_mwt": "",
        "quality_status": "needs_review",
        "notes": "Campus corretto da titolo MASE; scartato riferimento spurio a ML9. Candidati MWt presenti ma da verificare.",
    },
    "11813": {
        "display_project": "Data Center Campus 133 Generatori",
        "primary_developer": "KRYALOS SGR S.P.A.",
        "primary_proponent": "KRYALOS SGR S.P.A.",
        "campus_codes": "",
        "primary_thermal_power_mwt": "1000",
        "quality_status": "needs_review",
        "notes": "Titolo MASE indica 133 generatori e circa 1.000 MWt. Valore da verificare su elaborato tecnico.",
    },
    "11899": {
        "display_project": "Equinix ML10-ML11",
        "primary_developer": "Equinix Hyperscale 2 (ML10) Srl",
        "primary_proponent": "Equinix Hyperscale 2 (ML10) Srl",
        "campus_codes": "ML10 | ML11",
        "primary_thermal_power_mwt": "",
        "quality_status": "needs_review",
        "notes": "Campus e proponente corretti da target MASE; scartati riferimenti contaminanti a Vantage/ML7/ML8/ML9/MXP2.",
    },
    "11970": {
        "display_project": "AWS Zibido San Giacomo",
        "primary_developer": "AMAZON DATA SERVICES ITALY S.R.L.",
        "primary_proponent": "AMAZON DATA SERVICES ITALY S.R.L.",
        "campus_codes": "",
        "primary_thermal_power_mwt": "",
        "quality_status": "needs_review",
        "notes": "Identità progetto/proponente normalizzata da target MASE. Candidati MWt presenti ma da verificare.",
    },
}


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = read_csv(DASHBOARD)

    if not rows:
        raise FileNotFoundError(f"No dashboard rows found in {DASHBOARD}")

    fieldnames = list(rows[0].keys())

    for row in rows:
        object_id = clean(row.get("mase_object_id"))
        override = CURATED.get(object_id)

        if not override:
            continue

        for key, value in override.items():
            if key in row:
                row[key] = value

        # Lascia traccia che la riga è stata curata.
        if "notes" in row:
            note = clean(row.get("notes"))
            marker = "Curated by app.mase_dashboard_curator."
            row["notes"] = (note + " " + marker).strip() if marker not in note else note

    write_csv(DASHBOARD, rows, fieldnames)

    print(f"[OK] Curated {DASHBOARD} with {len(CURATED)} override rules")


if __name__ == "__main__":
    main()
