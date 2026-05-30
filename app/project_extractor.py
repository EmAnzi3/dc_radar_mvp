from pathlib import Path
from datetime import datetime
import re

import pandas as pd
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/contractor_sites")


PROJECT_PATTERNS = [
    r"\bML7\b",
    r"\bML8\b",
    r"\bML9\b",
    r"\bROM1\b",
    r"\bRom1\b",
    r"\bMXP1\b",
    r"\bMXP2\b",
    r"\bVantage\b",
    r"\bCyrusOne\b",
    r"\bDigital Realty\b",
    r"\bDATA4\b",
    r"\bMicrosoft\b",
    r"\bBornasco\b",
    r"\bSettimo Milanese\b",
    r"\bLacchiarella\b",
]


EXPLICIT_DEVELOPER_TOKENS = {
    "Digital Realty": "Digital Realty",
    "Vantage": "Vantage Data Centers",
    "CyrusOne": "CyrusOne",
    "DATA4": "DATA4",
    "Microsoft": "Microsoft",
}


EXPLICIT_LOCATION_TOKENS = {
    "Bornasco": "Bornasco",
    "Settimo Milanese": "Settimo Milanese",
    "Lacchiarella": "Lacchiarella",
}


PROJECT_LOCATION_HINTS = {
    "ROM1": "Roma",
    "Rom1": "Roma",
    "MXP2": "Settimo Milanese / area Milano",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_token(token: str) -> str:
    if token.lower() == "rom1":
        return "ROM1"
    return token


def normalize_url(url: str) -> str:
    return str(url or "").strip().rstrip("/")


def find_patterns(text: str) -> list[str]:
    found = []
    for pattern in PROJECT_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            found.append(normalize_token(match.group(0)))
    return sorted(set(found), key=lambda x: x.lower())


def infer_developer(token: str) -> str:
    # Solo associazioni esplicite: niente ereditarieta' da altri token nella stessa pagina.
    for key, value in EXPLICIT_DEVELOPER_TOKENS.items():
        if key.lower() == token.lower():
            return value
    return ""


def infer_location(token: str) -> str:
    for key, value in EXPLICIT_LOCATION_TOKENS.items():
        if key.lower() == token.lower():
            return value

    for key, value in PROJECT_LOCATION_HINTS.items():
        if key.lower() == token.lower():
            return value

    return ""


def infer_confidence(url: str, title: str, token: str, evidence: str) -> int:
    blob = f"{url} {title}".lower()

    if "realizzazioni-data-center" in blob:
        if token.upper() in ["ML7", "ML8", "ML9"]:
            return 75
        return 90

    if token.lower() in blob:
        return 80

    if token.lower() in str(evidence or "").lower():
        return 60

    return 40


def load_raw_html_for_source(source_name: str) -> str:
    if not RAW_DIR.exists():
        return ""

    safe = re.sub(r"[^0-9A-Za-z_-]+", "_", source_name.lower())
    raw_path = RAW_DIR / f"{safe}_home.html"

    if raw_path.exists():
        html = raw_path.read_text(encoding="utf-8", errors="ignore")
        return clean_text(BeautifulSoup(html, "lxml").get_text(" "))

    return ""


def run():
    source_file = OUTPUT_DIR / "contractor_site_hits.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun contractor_site_hits.csv trovato")
        return

    hits = pd.read_csv(source_file)
    rows = []

    seen = set()

    for _, row in hits.iterrows():
        source_name = row.get("source_name", "")
        url = normalize_url(row.get("url", ""))
        title = str(row.get("title", "") or "")
        text_sample = str(row.get("text_sample", "") or "")
        keyword_hits = str(row.get("keyword_hits", "") or "")

        raw_text = load_raw_html_for_source(source_name)

        blob = f"{title} {url} {text_sample} {raw_text}"
        tokens = find_patterns(blob)

        if not tokens:
            continue

        for token in tokens:
            developer = infer_developer(token)
            location = infer_location(token)
            confidence = infer_confidence(url, title, token, text_sample)

            key = (
                source_name.lower(),
                normalize_url(url).lower(),
                token.lower(),
            )

            if key in seen:
                continue

            seen.add(key)

            rows.append({
                "project_token": token,
                "project": token,
                "developer": developer,
                "location": location,
                "region": "",
                "contractor": source_name,
                "role": "contractor portfolio / site evidence",
                "package": "data center construction",
                "confidence": confidence,
                "evidence": text_sample[:500],
                "keyword_hits": keyword_hits,
                "source_url": url,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    out = OUTPUT_DIR / "contractor_project_leads.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(rows)} righe)")


if __name__ == "__main__":
    run()
