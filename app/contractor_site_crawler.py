from pathlib import Path
from datetime import datetime
import re
import os

import pandas as pd
import requests
from bs4 import BeautifulSoup


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/contractor_sites")

CONTRACTOR_TYPES = ["contractor", "engineering"]

KEYWORDS = [
    "data center",
    "datacenter",
    "data centre",
    "hyperscale",
    "digital realty",
    "cyrusone",
    "microsoft",
    "vantage",
    "data4",
    "equinix",
    "general contractor",
    "epc",
    "design and build",
    "construction",
    "mep",
    "civil works",
    "commissioning",
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def keyword_hits(text: str) -> str:
    low = text.lower()
    hits = [kw for kw in KEYWORDS if kw in low]
    return "; ".join(sorted(set(hits)))


def fetch(url: str) -> tuple[int, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 DC Radar MVP"
    }
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code, response.text


def make_absolute_url(base_url: str, href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href

    base = base_url.rstrip("/")

    if href.startswith("/"):
        parts = base.replace("https://", "").replace("http://", "").split("/")
        domain = parts[0]
        scheme = "https://" if base_url.startswith("https://") else "http://"
        return scheme + domain + href

    return base + "/" + href


def extract_candidate_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()

    interesting_terms = [
        "data",
        "datacenter",
        "data-center",
        "data-centre",
        "realizzazioni",
        "projects",
        "case",
        "news",
        "press",
        "media",
        "construction",
    ]

    for a in soup.find_all("a"):
        href = a.get("href")
        text = clean_text(a.get_text(" "))
        blob = f"{href or ''} {text}".lower()

        if any(term in blob for term in interesting_terms):
            url = make_absolute_url(base_url, href)
            if url:
                links.add(url)

    return sorted(links)


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    watchlist_name = os.getenv("SOURCE_WATCHLIST_FILE", "source_watchlist.csv")
    watchlist_file = INPUT_DIR / watchlist_name

    if not watchlist_file.exists() or watchlist_file.stat().st_size == 0:
        print("Nessuna source_watchlist trovata")
        return

    watchlist = pd.read_csv(watchlist_file)
    watchlist = watchlist[watchlist["source_type"].isin(CONTRACTOR_TYPES)]

    rows = []

    for _, row in watchlist.iterrows():
        source_name = row.get("source_name", "")
        source_type = row.get("source_type", "")
        priority = row.get("priority", "")
        base_url = str(row.get("base_url", "") or "").strip()

        if not base_url:
            continue

        print(f"CONTRACTOR CRAWL: {source_name} - {base_url}")

        urls_to_check = [base_url]

        try:
            status_code, html = fetch(base_url)
            raw_name = re.sub(r"[^0-9A-Za-z_-]+", "_", source_name.lower())
            (RAW_DIR / f"{raw_name}_home.html").write_text(html, encoding="utf-8", errors="ignore")

            urls_to_check.extend(extract_candidate_links(base_url, html)[:20])

        except Exception as exc:
            rows.append({
                "source_name": source_name,
                "source_type": source_type,
                "priority": priority,
                "url": base_url,
                "status_code": "",
                "keyword_hits": "",
                "title": "",
                "text_sample": "",
                "error": str(exc),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        seen = set()

        for url in urls_to_check:
            if url in seen:
                continue
            seen.add(url)

            try:
                status_code, html = fetch(url)
                soup = BeautifulSoup(html, "lxml")
                title = clean_text(soup.title.get_text(" ")) if soup.title else ""
                text = clean_text(soup.get_text(" "))
                hits = keyword_hits(text + " " + title + " " + url)

                if hits:
                    rows.append({
                        "source_name": source_name,
                        "source_type": source_type,
                        "priority": priority,
                        "url": url,
                        "status_code": status_code,
                        "keyword_hits": hits,
                        "title": title,
                        "text_sample": text[:700],
                        "error": "",
                        "checked_at": datetime.now().isoformat(timespec="seconds"),
                    })

            except Exception as exc:
                rows.append({
                    "source_name": source_name,
                    "source_type": source_type,
                    "priority": priority,
                    "url": url,
                    "status_code": "",
                    "keyword_hits": "",
                    "title": "",
                    "text_sample": "",
                    "error": str(exc),
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                })

    out = OUTPUT_DIR / "contractor_site_hits.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(rows)} righe)")


if __name__ == "__main__":
    run()



