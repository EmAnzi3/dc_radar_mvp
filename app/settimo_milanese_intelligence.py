from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/local_authorities/settimo_milanese")

BASE_URL = "https://www.comune.settimomilanese.mi.it"

KEYWORDS = [
    "data center",
    "datacenter",
    "techbau",
    "ml8",
    "ml9",
    "ml7",
    "vantage",
    "equinix",
    "permesso di costruire",
    "suap",
    "conferenza dei servizi",
    "piano attuativo",
    "variante urbanistica",
    "determinazione",
    "delibera",
]


SEED_PATHS = [
    "/",
    "/it",
    "/it/page/albo-pretorio",
    "/it/page/amministrazione-trasparente",
    "/it/page/urbanistica-ed-edilizia-privata",
    "/it/page/suap",
    "/it/page/sportello-unico-attivita-produttive",
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_url(url: str) -> str:
    url = str(url or "").strip()
    url = url.split("#")[0]
    return url.rstrip("/")


def is_same_domain(url: str) -> bool:
    try:
        return urlparse(url).netloc in ["", "www.comune.settimomilanese.mi.it", "comune.settimomilanese.mi.it"]
    except Exception:
        return False


def keyword_hits(text: str) -> str:
    low = text.lower()
    return "; ".join([kw for kw in KEYWORDS if kw in low])


def fetch(url: str):
    headers = {"User-Agent": "Mozilla/5.0 DC Radar MVP"}
    try:
        r = requests.get(url, headers=headers, timeout=25)
        return r.status_code, r.text, ""
    except Exception as exc:
        return 0, "", str(exc)


def extract_links(base_url: str, html: str):
    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.find_all("a"):
        href = a.get("href")
        text = clean_text(a.get_text(" "))

        if not href:
            continue

        full = normalize_url(urljoin(base_url, href))

        if not is_same_domain(full):
            continue

        blob = f"{text} {full}".lower()

        if any(k in blob for k in [
            "albo",
            "trasparente",
            "urbanistica",
            "edilizia",
            "suap",
            "determin",
            "deliber",
            "conferenza",
            "permesso",
            "piano",
            "variante",
            "data-center",
            "datacenter",
            "data%20center",
            "document",
            ".pdf",
        ]):
            links.append({
                "link_text": text,
                "url": full,
            })

    unique = {}
    for item in links:
        unique[item["url"]] = item

    return list(unique.values())


def save_raw(url: str, html: str, idx: int):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^0-9A-Za-z_-]+", "_", url.replace(BASE_URL, "").strip("/") or "home")
    path = RAW_DIR / f"{idx:03d}_{safe[:80]}.html"
    path.write_text(html, encoding="utf-8", errors="ignore")
    return str(path)


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    queue = [normalize_url(urljoin(BASE_URL, path)) for path in SEED_PATHS]
    seen = set()
    rows = []

    max_pages = 80
    idx = 0

    while queue and len(seen) < max_pages:
        url = normalize_url(queue.pop(0))

        if url in seen:
            continue

        seen.add(url)
        idx += 1

        print(f"SETTIMO CRAWL: {url}")

        status, html, error = fetch(url)
        raw_path = ""

        if html:
            raw_path = save_raw(url, html, idx)

        text = ""
        title = ""

        if html:
            soup = BeautifulSoup(html, "lxml")
            title = clean_text(soup.title.get_text(" ")) if soup.title else ""
            text = clean_text(soup.get_text(" "))
            hits = keyword_hits(f"{title} {text} {url}")
            links = extract_links(url, html)

            for link in links:
                if link["url"] not in seen and link["url"] not in queue and len(queue) < 150:
                    queue.append(link["url"])
        else:
            hits = ""

        if hits or error:
            rows.append({
                "authority": "Comune di Settimo Milanese",
                "city": "Settimo Milanese",
                "province": "MI",
                "status_code": status,
                "page_title": title,
                "keyword_hits": hits,
                "text_sample": text[:1200],
                "source_url": url,
                "raw_path": raw_path,
                "error": error,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    out = OUTPUT_DIR / "settimo_milanese_local_hits.csv"

    if rows:
        df = pd.DataFrame(rows).drop_duplicates(subset=["source_url", "keyword_hits"])
    else:
        df = pd.DataFrame(columns=[
            "authority", "city", "province", "status_code", "page_title",
            "keyword_hits", "text_sample", "source_url", "raw_path",
            "error", "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()
