from pathlib import Path
from datetime import datetime
import re
import time
import random

import pandas as pd
import requests
from bs4 import BeautifulSoup


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")
RAW_DIR = Path("data/raw/mase_discovery")

BASE_URL = "https://va.mite.gov.it/it-IT/Oggetti/Info/{object_id}"

KEYWORDS = [
    "data center",
    "datacenter",
    "centro elaborazione dati",
    "gruppi elettrogeni",
    "generatori",
    "equinix",
    "vantage",
    "microsoft",
    "digital realty",
    "cyrusone",
    "data4",
    "cloudhq",
    "retelit",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def keyword_hits(text):
    low = text.lower()
    return "; ".join([k for k in KEYWORDS if k in low])


def fetch(url):
    headers = {"User-Agent": "Mozilla/5.0 DC Radar MVP"}
    try:
        r = requests.get(url, headers=headers, timeout=25)
        return r.status_code, r.text, ""
    except Exception as exc:
        return 0, "", str(exc)


def extract_title(text):
    patterns = [
        r"(Progetto .+?)(?: - | Valutazioni| VAS| VIA| AIA|$)",
        r"(Installazione .+?)(?: - | Valutazioni| VAS| VIA| AIA|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return clean(m.group(1))[:300]

    return clean(text[:250])


def extract_proponent(text):
    patterns = [
        r"Proponente\s*:?\s*(.+?)(?:\s+Tipologia|\s+Procedura|\s+Autorità|\s+Regione|\s+Localizzazione|\s+Data|\s+Oggetto|\s+Descrizione|$)",
        r"Proponente\s+(.+?)(?:\s+Tipologia|\s+Procedura|\s+Autorità|\s+Regione|\s+Localizzazione|\s+Data|\s+Oggetto|\s+Descrizione|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            value = clean(m.group(1))
            if 2 <= len(value) <= 180:
                return value

    return ""


def extract_region(text):
    for region in [
        "Lombardia", "Lazio", "Piemonte", "Veneto", "Emilia-Romagna",
        "Toscana", "Puglia", "Campania", "Sicilia", "Sardegna"
    ]:
        if region.lower() in text.lower():
            return region
    return ""


def extract_location_hints(text):
    cities = [
        "Settimo Milanese", "Milano", "Roma", "Cornaredo", "Bornasco",
        "Lacchiarella", "Segrate", "Vittuone", "Pomezia", "Melegnano"
    ]
    found = [c for c in cities if c.lower() in text.lower()]
    return "; ".join(found)


def save_raw(object_id, html):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"mase_info_{object_id}.html"
    path.write_text(html, encoding="utf-8", errors="ignore")
    return str(path)


def read_ranges():
    path = INPUT_DIR / "mase_discovery_ranges.csv"
    if not path.exists() or path.stat().st_size == 0:
        return [(8500, 11200, "high", "default range")]

    df = pd.read_csv(path).fillna("")
    ranges = []

    for _, r in df.iterrows():
        ranges.append((
            int(r.get("start_id")),
            int(r.get("end_id")),
            str(r.get("priority", "")),
            str(r.get("notes", "")),
        ))

    return ranges


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for start_id, end_id, priority, notes in read_ranges():
        for object_id in range(start_id, end_id + 1):
            url = BASE_URL.format(object_id=object_id)
            print(f"MASE DISCOVERY: {object_id}")

            status, html, error = fetch(url)

            if error:
                continue

            if status != 200 or not html:
                continue

            soup = BeautifulSoup(html, "lxml")
            text = clean(soup.get_text(" "))
            title_tag = clean(soup.title.get_text(" ")) if soup.title else ""

            hits = keyword_hits(f"{title_tag} {text}")

            if not hits:
                continue

            raw_path = save_raw(object_id, html)

            rows.append({
                "mase_object_id": object_id,
                "title": extract_title(text),
                "proponent": extract_proponent(text),
                "region": extract_region(text),
                "location_hints": extract_location_hints(text),
                "keyword_hits": hits,
                "source_url": url,
                "status_code": status,
                "priority": priority,
                "notes": notes,
                "text_sample": text[:1200],
                "raw_path": raw_path,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

            time.sleep(random.uniform(0.15, 0.35))

    out = OUTPUT_DIR / "mase_discovered_objects.csv"

    if rows:
        df = pd.DataFrame(rows).drop_duplicates(subset=["mase_object_id"])
        df = df.sort_values(by=["mase_object_id"])
    else:
        df = pd.DataFrame(columns=[
            "mase_object_id", "title", "proponent", "region", "location_hints",
            "keyword_hits", "source_url", "status_code", "priority", "notes",
            "text_sample", "raw_path", "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} oggetti trovati)")


if __name__ == "__main__":
    run()
