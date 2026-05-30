from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")


DEDICATED_PROJECT_URL_PATTERNS = [
    "/realizzazioni/ml7",
    "/realizzazioni/ml8",
    "/realizzazioni/ml9",
    "/realizzazioni/vantage",
    "/realizzazioni/digital-realty-rom1",
]


def clean_text(value) -> str:
    value = "" if pd.isna(value) else str(value)
    return re.sub(r"\s+", " ", value).strip()


def is_dedicated_project_page(url: str) -> bool:
    url = clean_text(url).lower().rstrip("/")
    return any(pattern in url for pattern in DEDICATED_PROJECT_URL_PATTERNS)


def to_number(value: str):
    if not value:
        return ""

    raw = str(value).strip()

    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")

    try:
        num = float(raw)
        if num.is_integer():
            return int(num)
        return num
    except Exception:
        return ""


def normalize_project(value: str) -> str:
    value = clean_text(value)
    if value.lower() == "rom1":
        return "ROM1"
    return value


def extract_city_province(text: str, project: str):
    project = normalize_project(project)

    pattern = rf"Data Center\s+{re.escape(project)}\s+(.{{0,80}}?)\s*[–-]\s*([A-Z]{{2}})\s*\|\s*Italia"
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if match:
        city_blob = clean_text(match.group(1))

        for prefix in ["Equinix", "Vantage", "Digital Realty", "Microsoft", "DATA4", "CyrusOne"]:
            if city_blob.lower().startswith(prefix.lower() + " "):
                city_blob = clean_text(city_blob[len(prefix):])

        if city_blob and len(city_blob) <= 60 and "CHI SIAMO" not in city_blob.upper():
            return city_blob, match.group(2).strip()

    fallback_locations = {
        "ML7": ("Settimo Milanese", "MI"),
        "ML8": ("Settimo Milanese", "MI"),
        "ML9": ("Settimo Milanese", "MI"),
        "Vantage": ("Settimo Milanese", "MI"),
        "ROM1": ("Roma", "RM"),
    }

    if project in fallback_locations:
        return fallback_locations[project]

    return "", ""


def extract_area_sqm(text: str):
    patterns = [
        r"area di circa\s*([\d\.\,]+)\s*mq",
        r"lotto di ca\.\s*([\d\.\,]+)\s*mq",
        r"si estende su\s*([\d\.\,]+)\s*mq",
        r"si sviluppa su\s*([\d\.\,]+)\s*mq",
        r"superficie di circa\s*([\d\.\,]+)\s*mq",
        r"([\d\.\,]+)\s*mq\s*Area",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return to_number(match.group(1))

    return ""


def extract_built_sqm(text: str):
    patterns = [
        r"superficie costruita pari a\s*([\d\.\,]+)\s*mq",
        r"built area\s*([\d\.\,]+)\s*mq",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return to_number(match.group(1))

    return ""


def extract_it_power_mw(text: str):
    patterns = [
        r"capacità complessiva di\s*([\d\.\,]+)\s*MW\s*IT",
        r"potenza IT di\s*([\d\.\,]+)\s*MW",
        r"capacità IT complessiva di\s*([\d\.\,]+)\s*MW",
        r"([\d\.\,]+)\s*MW\s*IT\s*Total power",
        r"([\d\.\,]+)\s*MW\s*IT",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return to_number(match.group(1))

    return ""


def extract_data_halls(text: str):
    match = re.search(r"(\d+)\s*data hall", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return ""


def extract_dates(text: str):
    start = ""
    end = ""

    start_match = re.search(r"Inizio:\s*(\d{2})\s*/\s*(\d{4})", text, flags=re.IGNORECASE)
    end_match = re.search(r"Fine:\s*(\d{2})\s*/\s*(\d{4})", text, flags=re.IGNORECASE)

    if start_match:
        start = f"{start_match.group(2)}-{start_match.group(1)}"

    if end_match:
        end = f"{end_match.group(2)}-{end_match.group(1)}"

    return start, end


def extract_work_scope(text: str):
    match = re.search(
        r"Scopo del lavoro:\s*(.+?)(?:Cliente:|Inizio:|Fine:|torna a progetti|CHI SIAMO|$)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(1)).rstrip(".")

    return ""


def infer_confidence(row: dict, facts: dict) -> int:
    score = 50

    if clean_text(row.get("project")):
        score += 10
    if facts.get("city"):
        score += 10
    if facts.get("it_power_mw"):
        score += 10
    if facts.get("work_scope"):
        score += 10
    if facts.get("start_date") or facts.get("end_date"):
        score += 10

    return min(score, 100)


def run():
    source_file = OUTPUT_DIR / "contractor_project_pages.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun contractor_project_pages.csv trovato")
        return

    pages = pd.read_csv(source_file)
    rows = []

    for _, row in pages.iterrows():
        project = normalize_project(row.get("project", ""))
        contractor = clean_text(row.get("contractor", ""))
        source_url = clean_text(row.get("source_url", ""))
        text = clean_text(row.get("text_sample", ""))

        if not project:
            continue

        if not is_dedicated_project_page(source_url):
            continue

        city, province = extract_city_province(text, project)
        start_date, end_date = extract_dates(text)

        facts = {
            "city": city,
            "province": province,
            "area_sqm": extract_area_sqm(text),
            "built_sqm": extract_built_sqm(text),
            "it_power_mw": extract_it_power_mw(text),
            "data_halls": extract_data_halls(text),
            "start_date": start_date,
            "end_date": end_date,
            "work_scope": extract_work_scope(text),
        }

        if not any(facts.values()):
            continue

        rows.append({
            "contractor": contractor,
            "project": project,
            "developer": clean_text(row.get("developer", "")),
            "city": facts["city"],
            "province": facts["province"],
            "region": "",
            "area_sqm": facts["area_sqm"],
            "built_sqm": facts["built_sqm"],
            "it_power_mw": facts["it_power_mw"],
            "data_halls": facts["data_halls"],
            "start_date": facts["start_date"],
            "end_date": facts["end_date"],
            "work_scope": facts["work_scope"],
            "source_url": source_url,
            "confidence": infer_confidence(row, facts),
            "evidence": text[:900],
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    out = OUTPUT_DIR / "contractor_project_facts.csv"

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
