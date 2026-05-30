from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")


def clean_text(value) -> str:
    value = "" if pd.isna(value) else str(value)
    return re.sub(r"\s+", " ", value).strip()


def to_number(value: str):
    if not value:
        return ""

    raw = str(value)
    raw = raw.replace("€", "").replace(",", "").replace(".", "")
    raw = re.sub(r"[^\d]", "", raw)

    if not raw:
        return ""

    try:
        return int(raw)
    except Exception:
        return ""


def extract_project(title: str, text: str):
    title = clean_text(title)

    if " - Mercury Engineering" in title:
        return title.replace(" - Mercury Engineering", "").strip()

    match = re.search(
        r"(Hyperscale Data Centres|Enterprise Data Centres)\s+(.+?)\s+Location",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(2))

    return ""


def extract_location(text: str):
    match = re.search(r"Location\s+(.+?)\s+Timeframe", text, flags=re.IGNORECASE)
    if match:
        location = clean_text(match.group(1))
        parts = [x.strip() for x in location.split(",")]

        city = parts[0] if len(parts) >= 1 else ""
        country = parts[-1] if len(parts) >= 2 else ""

        return city, country

    return "", ""


def extract_timeframe(text: str):
    match = re.search(r"Timeframe\s+(.+?)\s+Client", text, flags=re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_client(text: str):
    match = re.search(r"Client\s+(.+?)\s+Value", text, flags=re.IGNORECASE)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_value_eur(text: str):
    match = re.search(r"Value\s+€\s*([\d,\.]+)", text, flags=re.IGNORECASE)
    if match:
        return to_number(match.group(1))
    return ""


def extract_services(text: str):
    match = re.search(
        r"SERVICES\s+(.+?)(?:Project Details|Projects|About|Who We Are|Contact|$)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(1))[:300]
    return ""


def is_mercury_project_page(row) -> bool:
    contractor = clean_text(row.get("contractor", ""))
    url = clean_text(row.get("source_url", "")).lower()
    title = clean_text(row.get("page_title", "")).lower()

    return (
        contractor.lower() == "mercury engineering"
        and "/project/" in url
        and "data centre" in title
    )


def run():
    source_file = OUTPUT_DIR / "contractor_project_pages.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun contractor_project_pages.csv trovato")
        return

    pages = pd.read_csv(source_file)
    rows = []

    for _, row in pages.iterrows():
        if not is_mercury_project_page(row):
            continue

        title = clean_text(row.get("page_title", ""))
        text = clean_text(row.get("text_sample", ""))
        source_url = clean_text(row.get("source_url", ""))

        project = extract_project(title, text)
        city, country = extract_location(text)
        timeframe = extract_timeframe(text)
        client = extract_client(text)
        value_eur = extract_value_eur(text)
        services = extract_services(text)

        if not project:
            continue

        rows.append({
            "contractor": "Mercury Engineering",
            "project": project,
            "developer": client,
            "city": city,
            "country": country,
            "region": "",
            "contract_value_eur": value_eur,
            "timeframe": timeframe,
            "work_scope": services,
            "source_url": source_url,
            "confidence": 90 if client else 80,
            "evidence": text[:900],
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    out = OUTPUT_DIR / "mercury_projects.csv"

    if rows:
        df = pd.DataFrame(rows).drop_duplicates(
            subset=["contractor", "project", "source_url"]
        )
    else:
        df = pd.DataFrame()

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()
