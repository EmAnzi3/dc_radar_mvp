from pathlib import Path
from datetime import datetime
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/mase_document_pages")

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
    "gruppi elettrogeni",
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_page(url: str) -> tuple[int, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 DC Radar MVP"
    }
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code, response.text


def make_absolute_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return "https://va.mite.gov.it" + href
    return "https://va.mite.gov.it/" + href


def keyword_hits(text: str) -> str:
    low = text.lower()
    hits = [kw for kw in KEYWORDS if kw in low]
    return "; ".join(sorted(set(hits)))


def extract_download_links(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []

    for a in soup.find_all("a"):
        text = clean_text(a.get_text(" "))
        href = make_absolute_url(a.get("href"))
        blob = f"{text} {href}".lower()

        if not href:
            continue

        if (
            "download" in blob
            or "documenti" in blob
            or "allegati" in blob
            or ".pdf" in blob
            or ".zip" in blob
            or ".p7m" in blob
        ):
            rows.append({
                "file_title": text,
                "file_url": href,
                "keyword_hits": keyword_hits(blob),
            })

    return rows


def run():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_file = OUTPUT_DIR / "mase_documents.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun mase_documents.csv trovato")
        return

    docs = pd.read_csv(source_file)

    if "document_url" not in docs.columns:
        print("mase_documents.csv non contiene document_url")
        return

    rows = []

    doc_urls = (
        docs["document_url"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    for url in sorted(set(doc_urls)):
        if not url:
            continue

        matching = docs[docs["document_url"].astype(str) == url].iloc[0]

        project = matching.get("project", "")
        developer = matching.get("developer", "")
        location = matching.get("location", "")
        region = matching.get("region", "")
        object_id = matching.get("mase_object_id", "")

        print(f"MASE DOC: analizzo {project} - {url}")

        try:
            status_code, html = fetch_page(url)
            raw_name = re.sub(r"[^0-9A-Za-z_-]+", "_", url.split("/")[-2] + "_" + url.split("/")[-1])
            raw_path = RAW_DIR / f"{raw_name}.html"
            raw_path.write_text(html, encoding="utf-8", errors="ignore")

            page_text = clean_text(BeautifulSoup(html, "lxml").get_text(" "))
            page_hits = keyword_hits(page_text)

            links = extract_download_links(html)

            if not links:
                rows.append({
                    "project": project,
                    "developer": developer,
                    "location": location,
                    "region": region,
                    "mase_object_id": object_id,
                    "document_page_url": url,
                    "status_code": status_code,
                    "file_title": "",
                    "file_url": "",
                    "keyword_hits": page_hits,
                    "page_text_sample": page_text[:500],
                    "error": "",
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                })

            for link in links:
                rows.append({
                    "project": project,
                    "developer": developer,
                    "location": location,
                    "region": region,
                    "mase_object_id": object_id,
                    "document_page_url": url,
                    "status_code": status_code,
                    "file_title": link.get("file_title", ""),
                    "file_url": link.get("file_url", ""),
                    "keyword_hits": link.get("keyword_hits", "") or page_hits,
                    "page_text_sample": page_text[:500],
                    "error": "",
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                })

        except Exception as exc:
            rows.append({
                "project": project,
                "developer": developer,
                "location": location,
                "region": region,
                "mase_object_id": object_id,
                "document_page_url": url,
                "status_code": "",
                "file_title": "",
                "file_url": "",
                "keyword_hits": "",
                "page_text_sample": "",
                "error": str(exc),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    out = OUTPUT_DIR / "mase_document_files.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(rows)} righe)")


if __name__ == "__main__":
    run()
