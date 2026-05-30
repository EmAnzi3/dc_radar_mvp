from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")


CLIENT_PATTERNS = [
    r"Cliente:\s*([A-ZÀ-Úa-zà-ú0-9 &\.\-]+?)(?:\s+Inizio:|\s+Fine:|\s+torna a progetti|$)",
    r"realizzato per\s*([A-ZÀ-Úa-zà-ú0-9 &\.\-]+?)(?:\s*,|\s+si estende|\s+si sviluppa|\s+torna a progetti|$)",
    r"realizzata per\s*([A-ZÀ-Úa-zà-ú0-9 &\.\-]+?)(?:\s*,|\s+si estende|\s+si sviluppa|\s+torna a progetti|$)",
]


def clean_text(value) -> str:
    value = "" if pd.isna(value) else str(value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_developer(value: str) -> str:
    value = clean_text(value)

    replacements = {
        "Vantage": "Vantage Data Centers",
        "Digital Realty": "Digital Realty",
        "Equinix": "Equinix",
        "DATA4": "DATA4",
        "Microsoft": "Microsoft",
        "CyrusOne": "CyrusOne",
    }

    for key, normalized in replacements.items():
        if key.lower() in value.lower():
            return normalized

    return value


def infer_developer(text: str, existing_value="") -> str:
    existing_value = clean_text(existing_value)

    if existing_value:
        return normalize_developer(existing_value)

    for pattern in CLIENT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_developer(match.group(1))

    return ""


def infer_status(start_date: str, end_date: str) -> str:
    today = "2026-05"

    if start_date and end_date:
        if start_date <= today <= end_date:
            return "In costruzione"
        if today < start_date:
            return "Programmato"
        if today > end_date:
            return "Concluso / da verificare"

    if start_date and not end_date:
        if start_date <= today:
            return "Avviato / da verificare"
        return "Programmato"

    return "Da verificare"


def run():
    source_file = OUTPUT_DIR / "contractor_project_facts.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun contractor_project_facts.csv trovato")
        return

    facts = pd.read_csv(source_file)
    rows = []

    for _, row in facts.iterrows():
        evidence = clean_text(row.get("evidence", ""))
        developer = infer_developer(evidence, row.get("developer", ""))

        project = clean_text(row.get("project", ""))
        contractor = clean_text(row.get("contractor", ""))
        city = clean_text(row.get("city", ""))
        province = clean_text(row.get("province", ""))
        source_url = clean_text(row.get("source_url", ""))
        start_date = clean_text(row.get("start_date", ""))
        end_date = clean_text(row.get("end_date", ""))

        if not project:
            continue

        rows.append({
            "developer": developer,
            "project": project,
            "city": city,
            "province": province,
            "region": clean_text(row.get("region", "")),
            "it_power_mw": row.get("it_power_mw", ""),
            "area_sqm": row.get("area_sqm", ""),
            "built_sqm": row.get("built_sqm", ""),
            "data_halls": row.get("data_halls", ""),
            "contractor": contractor,
            "work_scope": row.get("work_scope", ""),
            "start_date": start_date,
            "end_date": end_date,
            "status": infer_status(start_date, end_date),
            "source_url": source_url,
            "confidence": row.get("confidence", ""),
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    out = OUTPUT_DIR / "developer_master.csv"

    if rows:
        df = pd.DataFrame(rows)
        df = df.drop_duplicates(subset=["developer", "project", "contractor", "source_url"])
    else:
        df = pd.DataFrame()

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()
