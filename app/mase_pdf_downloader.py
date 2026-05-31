from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/mase_pdfs")


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except Exception:
        return pd.DataFrame()


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_filename(value):
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", str(value or ""))
    return value[:180]


def fetch(url):
    headers = {"User-Agent": "Mozilla/5.0 DC Radar MVP"}
    r = requests.get(url, headers=headers, timeout=45)
    return r.status_code, r.text


def download_file(url, path, max_attempts=4):
    headers = {"User-Agent": "Mozilla/5.0 DC Radar MVP"}

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            with requests.get(url, headers=headers, timeout=90, stream=True) as r:
                r.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                return r.status_code, r.headers.get("content-type", "")
        except Exception as exc:
            last_error = exc
            time.sleep(2 * attempt)

    raise last_error


def document_id_from_url(url):
    m = re.search(r"/File/Documento/(\d+)", str(url))
    return m.group(1) if m else ""


def extract_pdf_links(page_url, html):
    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.find_all("a"):
        href = a.get("href")
        text = clean(a.get_text(" "))
        if not href:
            continue

        full = urljoin(page_url, href)

        blob = f"{href} {text}".lower()

        if "/File/Documento/" in full or ".pdf" in blob or "formato pdf" in blob or "download" in blob:
            links.append({
                "pdf_url": full,
                "link_text": text,
            })

    unique = {}
    for item in links:
        unique[item["pdf_url"]] = item

    return list(unique.values())


def run():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    src = OUTPUT_DIR / "mase_document_files.csv"
    out = OUTPUT_DIR / "mase_pdf_files.csv"

    docs = read_csv_safe(src)

    rows = []

    if docs.empty:
        print("Nessun mase_document_files.csv trovato")
        pd.DataFrame().to_csv(out, index=False, encoding="utf-8-sig")
        return

    for _, r in docs.iterrows():
        doc_url = clean(r.get("document_page_url", ""))

        if not doc_url:
            continue

        print(f"MASE PDF PAGE: {doc_url}")

        try:
            status, html = fetch(doc_url)
        except Exception as exc:
            rows.append({
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "location": r.get("location", ""),
                "region": r.get("region", ""),
                "mase_object_id": r.get("mase_object_id", ""),
                "document_page_url": doc_url,
                "pdf_url": "",
                "link_text": "",
                "local_path": "",
                "status_code": "",
                "content_type": "",
                "error": str(exc),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        links = extract_pdf_links(doc_url, html)

        for i, link in enumerate(links, start=1):
            pdf_url = link["pdf_url"]
            document_id = document_id_from_url(pdf_url)
            filename = safe_filename(f'{r.get("mase_object_id","")}_{document_id or i}.pdf')
            local_path = RAW_DIR / filename

            try:
                print(f"MASE PDF DOWNLOAD: {pdf_url}")
                dl_status, content_type = download_file(pdf_url, local_path)
                error = ""
            except Exception as exc:
                dl_status = ""
                content_type = ""
                error = str(exc)
                local_path = Path("")

            rows.append({
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "location": r.get("location", ""),
                "region": r.get("region", ""),
                "mase_object_id": r.get("mase_object_id", ""),
                "document_page_url": doc_url,
                "pdf_url": pdf_url,
                "link_text": link["link_text"],
                "local_path": str(local_path),
                "status_code": dl_status,
                "content_type": content_type,
                "error": error,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    if rows:
        df = pd.DataFrame(rows).drop_duplicates(subset=["mase_object_id", "pdf_url"])
    else:
        df = pd.DataFrame(columns=[
            "project", "developer", "location", "region", "mase_object_id",
            "document_page_url", "pdf_url", "link_text", "local_path",
            "status_code", "content_type", "error", "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} PDF)")


if __name__ == "__main__":
    run()
