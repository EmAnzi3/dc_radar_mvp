from pathlib import Path
from datetime import datetime
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/mase")

KEYWORDS = [
    "general contractor",
    "epc",
    "impresa",
    "impresa esecutrice",
    "impresa affidataria",
    "appaltatore",
    "contraente",
    "costruttore",
    "progettista",
    "direzione lavori",
    "direttore lavori",
    "coordinatore sicurezza",
    "csp",
    "cse",
    "opere civili",
    "movimento terra",
    "fondazioni",
    "meccanico",
    "elettrico",
    "mep",
    "cabina",
    "sottostazione",
    "connessione",
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_page(url: str) -> tuple[int, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 DC Radar MVP"
    }
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code, response.text


def extract_links(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.find_all("a"):
        text = clean_text(a.get_text(" "))
        href = a.get("href")

        if not href:
            continue

        if href.startswith("/"):
            href = "https://va.mite.gov.it" + href

        combined = f"{text} {href}".lower()

        if any(keyword in combined for keyword in KEYWORDS) or "download" in combined or "document" in combined:
            links.append({
                "link_text": text,
                "url": href,
            })

    return links


def keyword_hits(text: str) -> str:
    low = text.lower()
    hits = [kw for kw in KEYWORDS if kw in low]
    return "; ".join(sorted(set(hits)))


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    csv_file = INPUT_DIR / "mase_targets.csv"

    if not csv_file.exists() or csv_file.stat().st_size == 0:
        print("Nessun target MASE trovato")
        return

    targets = pd.read_csv(csv_file)
    document_rows = []
    lead_rows = []

    for _, row in targets.iterrows():
        project = row.get("project", "")
        developer = row.get("developer", "")
        location = row.get("location", "")
        region = row.get("region", "")
        object_id = row.get("mase_object_id", "")
        source_url = row.get("source_url", "")

        print(f"MASE: analizzo {project} - {source_url}")

        try:
            status_code, html = fetch_page(source_url)
        except Exception as exc:
            document_rows.append({
                "project": project,
                "developer": developer,
                "location": location,
                "region": region,
                "mase_object_id": object_id,
                "source_url": source_url,
                "status_code": "",
                "link_text": "",
                "document_url": "",
                "keyword_hits": "",
                "error": str(exc),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        raw_file = RAW_DIR / f"{object_id}.html"
        raw_file.write_text(html, encoding="utf-8", errors="ignore")

        links = extract_links(html, source_url)
        page_hits = keyword_hits(html)

        if not links:
            document_rows.append({
                "project": project,
                "developer": developer,
                "location": location,
                "region": region,
                "mase_object_id": object_id,
                "source_url": source_url,
                "status_code": status_code,
                "link_text": "",
                "document_url": "",
                "keyword_hits": page_hits,
                "error": "",
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

        for link in links:
            text_blob = f"{link.get('link_text', '')} {link.get('url', '')}"
            hits = keyword_hits(text_blob)

            document_rows.append({
                "project": project,
                "developer": developer,
                "location": location,
                "region": region,
                "mase_object_id": object_id,
                "source_url": source_url,
                "status_code": status_code,
                "link_text": link.get("link_text", ""),
                "document_url": link.get("url", ""),
                "keyword_hits": hits,
                "error": "",
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

            if hits:
                lead_rows.append({
                    "project": project,
                    "developer": developer,
                    "location": location,
                    "region": region,
                    "company": "",
                    "role": "public_document_keyword_hit",
                    "package": "",
                    "evidence": link.get("link_text", ""),
                    "source_url": link.get("url", ""),
                    "confidence": 30,
                    "keyword_hits": hits,
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                })

    docs_df = pd.DataFrame(document_rows)
    leads_df = pd.DataFrame(lead_rows)

    docs_output = OUTPUT_DIR / "mase_documents.csv"
    leads_output = OUTPUT_DIR / "mase_contractor_leads.csv"

    docs_df.to_csv(docs_output, index=False, encoding="utf-8-sig")
    leads_df.to_csv(leads_output, index=False, encoding="utf-8-sig")

    print(f"Creato {docs_output} ({len(docs_df)} righe)")
    print(f"Creato {leads_output} ({len(leads_df)} righe)")


if __name__ == "__main__":
    run()
