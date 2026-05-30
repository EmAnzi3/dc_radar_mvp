from pathlib import Path
from datetime import datetime
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/project_pages")

KEYWORDS = [
    "data center",
    "datacenter",
    "data centre",
    "hyperscale",
    "mission critical",
    "case study",
    "case studies",
    "general contractor",
    "epc",
    "design and build",
    "construction",
    "mep",
    "civil works",
    "digital realty",
    "vantage",
    "cyrusone",
    "microsoft",
    "data4",
    "mercury",
    "ml7",
    "ml8",
    "ml9",
    "rom1",
]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def keyword_hits(text: str) -> str:
    low = text.lower()
    return "; ".join(sorted({kw for kw in KEYWORDS if kw in low}))


def normalize_url(url: str) -> str:
    return str(url or "").strip().rstrip("/")


def make_absolute_url(base_url: str, href: str) -> str:
    if not href:
        return ""

    if href.startswith("http"):
        return normalize_url(href)

    base = normalize_url(base_url)
    scheme = "https://" if base.startswith("https://") else "http://"
    domain = base.replace("https://", "").replace("http://", "").split("/")[0]

    if href.startswith("/"):
        return normalize_url(scheme + domain + href)

    return normalize_url(base + "/" + href)


def fetch(url: str) -> tuple[int, str]:
    headers = {"User-Agent": "Mozilla/5.0 DC Radar MVP"}
    response = requests.get(url, headers=headers, timeout=30)
    return response.status_code, response.text


def looks_like_project_link(url: str, text: str) -> bool:
    blob = f"{url} {text}".lower()

    positive = [
        "realizzazioni",
        "project",
        "projects",
        "case-study",
        "case-studies",
        "case_study",
        "case_studies",
        "mission-critical",
        "mission_critical",
        "data-center",
        "data_center",
        "data-centre",
        "data_centre",
        "datacenter",
        "rom1",
        "vantage",
        "ml7",
        "ml8",
        "ml9",
        "cyrusone",
        "digital-realty",
    ]

    negative = [
        "hotel",
        "residenziale",
        "studentati",
        "retail",
        "logistica",
        "energie-rinnovabili",
        "industriale",
        "uffici",
        "privacy",
        "cookie",
        "contatti",
        "lavora-con-noi",
        "careers",
        "contact",
    ]

    if any(term in blob for term in negative):
        return False

    return any(term in blob for term in positive)


def extract_links_from_page(base_url: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []

    for a in soup.find_all("a"):
        text = clean_text(a.get_text(" "))
        href = make_absolute_url(base_url, a.get("href"))

        if not href:
            continue

        if looks_like_project_link(href, text):
            rows.append({
                "link_text": text,
                "url": href,
            })

    unique = {}
    for row in rows:
        unique[normalize_url(row["url"])] = row

    return list(unique.values())


def infer_project_from_url_or_title(url: str, title: str, text: str) -> str:
    blob = f"{url} {title} {text}".lower()

    mapping = {
        "rom1": "ROM1",
        "ml7": "ML7",
        "ml8": "ML8",
        "ml9": "ML9",
        "vantage": "Vantage",
        "cyrusone": "CyrusOne",
        "digital-realty": "Digital Realty",
        "mercury": "Mercury",
        "mission critical": "Mission Critical",
        "mission-critical": "Mission Critical",
    }

    for key, value in mapping.items():
        if key in blob:
            return value

    return ""


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    source_file = OUTPUT_DIR / "contractor_site_hits.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun contractor_site_hits.csv trovato")
        return

    hits = pd.read_csv(source_file)

    candidate_pages = hits[
        hits["url"].astype(str).str.contains(
            "realizzazioni-data-center|data-center|data-centre|datacenter|mission-critical|case-study|case-studies|rom1|vantage|cyrusone",
            case=False,
            na=False,
        )
    ]

    rows = []
    checked = set()

    for _, row in candidate_pages.iterrows():
        contractor = row.get("source_name", "")
        source_url = normalize_url(row.get("url", ""))

        if not source_url or source_url in checked:
            continue

        checked.add(source_url)

        print(f"PROJECT EXPAND: {contractor} - {source_url}")

        try:
            status_code, html = fetch(source_url)
            links = extract_links_from_page(source_url, html)
            pages_to_visit = [{"link_text": "source_page", "url": source_url}] + links[:30]

            for item in pages_to_visit:
                page_url = normalize_url(item["url"])

                if not page_url:
                    continue

                try:
                    page_status, page_html = fetch(page_url)
                    soup = BeautifulSoup(page_html, "lxml")
                    title = clean_text(soup.title.get_text(" ")) if soup.title else ""
                    text = clean_text(soup.get_text(" "))
                    hits_text = keyword_hits(text + " " + title + " " + page_url)
                    project = infer_project_from_url_or_title(page_url, title, text)

                    safe_name = re.sub(r"[^0-9A-Za-z_-]+", "_", f"{contractor}_{project or 'page'}_{len(rows)}")
                    (RAW_DIR / f"{safe_name}.html").write_text(page_html, encoding="utf-8", errors="ignore")

                    if hits_text or project:
                        rows.append({
                            "contractor": contractor,
                            "project": project,
                            "developer": "",
                            "location": "",
                            "role": "contractor project page",
                            "package": "data center construction",
                            "confidence": 80 if project else 50,
                            "page_title": title,
                            "link_text": item.get("link_text", ""),
                            "keyword_hits": hits_text,
                            "text_sample": text[:900],
                            "source_url": page_url,
                            "checked_at": datetime.now().isoformat(timespec="seconds"),
                        })

                except Exception as exc:
                    rows.append({
                        "contractor": contractor,
                        "project": "",
                        "developer": "",
                        "location": "",
                        "role": "contractor project page",
                        "package": "data center construction",
                        "confidence": 0,
                        "page_title": "",
                        "link_text": item.get("link_text", ""),
                        "keyword_hits": "",
                        "text_sample": "",
                        "source_url": page_url,
                        "error": str(exc),
                        "checked_at": datetime.now().isoformat(timespec="seconds"),
                    })

        except Exception as exc:
            rows.append({
                "contractor": contractor,
                "project": "",
                "developer": "",
                "location": "",
                "role": "contractor project page",
                "package": "data center construction",
                "confidence": 0,
                "page_title": "",
                "link_text": "",
                "keyword_hits": "",
                "text_sample": "",
                "source_url": source_url,
                "error": str(exc),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    out = OUTPUT_DIR / "contractor_project_pages.csv"
    pd.DataFrame(rows).drop_duplicates().to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(rows)} righe)")


if __name__ == "__main__":
    run()
