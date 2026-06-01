from __future__ import annotations

import csv
import html
import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse, urldefrag

import requests


SOURCES = Path("data/input/external_sources/datacentermap_sources.csv")
ALIASES = Path("data/input/external_sources/known_project_aliases.csv")
MASTER_CSV = Path("data/output/dc_project_fused_master.csv")
MASTER_JSON = Path("docs/dc_project_fused_master.json")

OUT_CSV = Path("data/output/external_sources/datacentermap_candidates.csv")
OUT_HTML = Path("reports/site/external_sources/datacentermap_review.html")

MAX_FACILITIES = int(os.getenv("DCM_MAX_FACILITIES", "120"))
SLEEP_SECONDS = float(os.getenv("DCM_SLEEP", "0.8"))

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36"

TARGET_STATUSES = {
    "planned",
    "under construction",
    "land banked",
}

EXCLUDED_STATUSES = {
    "operational",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def canonical_url(url: str) -> str:
    url, _ = urldefrag(clean(url))
    return url


def safe_join(base_url: str, href: str) -> str:
    href = clean(href)
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return ""

    try:
        url = canonical_url(urljoin(base_url, href))
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return url
    except Exception:
        return ""


def fetch(url: str) -> tuple[str, str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        return r.text, ""
    except Exception as e:
        return "", str(e)


def html_to_lines(raw_html: str) -> list[str]:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text("\n", strip=True)
    except Exception:
        text = re.sub(r"(?is)<script.*?</script>", " ", raw_html)
        text = re.sub(r"(?is)<style.*?</style>", " ", text)
        text = re.sub(r"(?is)<[^>]+>", "\n", text)
        text = html.unescape(text)

    lines = []
    for line in text.splitlines():
        line = clean(line)
        if line:
            lines.append(line)
    return lines


def extract_h1(raw_html: str, fallback: str = "") -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(raw_html, "html.parser")
        h1 = soup.find("h1")
        if h1:
            return clean(h1.get_text(" ", strip=True))
    except Exception:
        pass

    m = re.search(r"<h1[^>]*>(.*?)</h1>", raw_html, re.I | re.S)
    if m:
        return clean(re.sub(r"<[^>]+>", " ", html.unescape(m.group(1))))

    return fallback


def extract_facility_links(market_url: str, raw_html: str) -> list[dict[str, str]]:
    parsed_market = urlparse(market_url)
    market_path = parsed_market.path.strip("/").split("/")

    # Expected: italy/milan
    if len(market_path) < 2:
        return []

    country_slug = market_path[0]
    market_slug = market_path[1]

    links: list[dict[str, str]] = []
    seen = set()

    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(raw_html, "html.parser")
        anchors = soup.find_all("a", href=True)
        for a in anchors:
            url = safe_join(market_url, a.get("href", ""))
            text = clean(a.get_text(" ", strip=True))
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")

            if len(parts) != 3:
                continue

            if parts[0] != country_slug or parts[1] != market_slug:
                continue

            if url == market_url or url in seen:
                continue

            if not text or text.lower() in {"data centers", "italy", "milan", "rome"}:
                continue

            seen.add(url)
            links.append({
                "facility_url": url,
                "market_listing_text": text,
            })
    except Exception:
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html, re.I | re.S):
            url = safe_join(market_url, html.unescape(m.group(1)))
            text = clean(re.sub(r"<[^>]+>", " ", html.unescape(m.group(2))))
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")

            if len(parts) == 3 and parts[0] == country_slug and parts[1] == market_slug and url not in seen:
                seen.add(url)
                links.append({
                    "facility_url": url,
                    "market_listing_text": text,
                })

    return links


def extract_status(lines: list[str]) -> str:
    blob = "\n".join(lines)

    m = re.search(r"currently listed as:\s*([A-Za-z ]+)", blob, re.I)
    if m:
        return clean(m.group(1)).title()

    m = re.search(r"New Stage:\s*([A-Za-z ]+)", blob, re.I)
    if m:
        return clean(m.group(1)).title()

    return ""


def extract_operator_address_description(title: str, lines: list[str]) -> tuple[str, str, str]:
    operator = ""
    address_parts: list[str] = []

    try:
        idx = lines.index(title)
    except ValueError:
        idx = -1

    if idx >= 0:
        after = lines[idx + 1 : idx + 12]

        skip = {
            "visit website",
            "data centers",
            "italy",
            "milan",
            "rome",
            "request quote",
        }

        for line in after:
            low = line.lower()
            if low in skip:
                continue
            if low.startswith("image:"):
                continue

            operator = line
            break

        if operator:
            start = after.index(operator) + 1
            for line in after[start:]:
                low = line.lower()

                if low in {"visit website", "events", "pricing & services", "advertisement"}:
                    break
                if low.startswith("image:"):
                    continue
                if "according to our data" in low:
                    continue

                # Prendi righe indirizzo finché sono plausibili.
                if len(address_parts) < 4:
                    address_parts.append(line)

    # Description: dopo Visit Website e prima di Events/Pricing/Nearest.
    description_parts: list[str] = []
    capture = False

    for line in lines:
        low = line.lower()

        if low == "visit website":
            capture = True
            continue

        if capture and low in {"events", "pricing & services", "advertisement", "nearest data centers", "shortlist data center request quote"}:
            break

        if capture:
            if low.startswith("image:"):
                continue
            if line == operator:
                continue
            if line in address_parts:
                continue
            if len(line) < 3:
                continue
            description_parts.append(line)

    return operator, ", ".join(address_parts), " ".join(description_parts[:8])


def google_maps_url(address: str, fallback: str) -> str:
    query = clean(address) or clean(fallback)
    if not query:
        return ""

    if "italy" not in query.lower() and "italia" not in query.lower():
        query = f"{query}, Italy"

    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def load_master_rows() -> list[dict[str, str]]:
    rows = read_csv(MASTER_CSV)
    if rows:
        return rows

    if not MASTER_JSON.exists():
        return []

    try:
        data = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ["records", "projects", "data", "rows"]:
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    return []


def load_aliases(master_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    aliases = read_csv(ALIASES)

    # Alias automatici molto prudenti: solo nome progetto e proponente specifico.
    for row in master_rows:
        project = clean(row.get("project"))
        if project:
            aliases.append({
                "project": project,
                "alias": project,
                "required_context": "",
            })

        proponent = clean(row.get("mase_proponent"))
        location = clean(row.get("location"))

        if proponent and len(proponent) >= 8 and location:
            aliases.append({
                "project": project,
                "alias": proponent,
                "required_context": location,
            })

    return aliases


def match_known_project(blob: str, aliases: list[dict[str, str]]) -> str:
    blob_norm = norm(blob)
    matches: list[str] = []

    for a in aliases:
        project = clean(a.get("project"))
        alias = norm(a.get("alias"))
        required = norm(a.get("required_context"))

        if not project or not alias:
            continue

        if len(alias) < 4:
            continue

        if alias not in blob_norm:
            continue

        if required and required not in blob_norm:
            continue

        if project not in matches:
            matches.append(project)

    return " | ".join(matches)


def classify(status: str, matched_project: str, title: str) -> tuple[str, str, str]:
    s = norm(status)

    if s in EXCLUDED_STATUSES:
        return "excluded_operational", "P4", "exclude_operational"

    if matched_project and s in TARGET_STATUSES:
        return "known_project_enrichment", "P2", "enrich_existing_project"

    if not matched_project and s in {"planned", "under construction"}:
        return "new_candidate_review", "P1", "manual_review_new_candidate"

    if not matched_project and s == "land banked":
        return "new_candidate_review", "P2", "manual_review_land_banked"

    if matched_project and not s:
        return "known_project_enrichment", "P3", "enrich_existing_project_status_unknown"

    if not s:
        return "status_unknown_review", "P3", "manual_review_status_unknown"

    return "discard_or_low_relevance", "P4", "discard"


def parse_facility(source: dict[str, str], link: dict[str, str], aliases: list[dict[str, str]]) -> dict[str, str]:
    url = clean(link.get("facility_url"))
    listing_text = clean(link.get("market_listing_text"))

    raw_html, error = fetch(url)
    if error:
        return {
            "market": clean(source.get("market")),
            "region_hint": clean(source.get("region_hint")),
            "facility_name": listing_text,
            "operator": "",
            "dcm_status": "",
            "address": "",
            "description": "",
            "source_url": url,
            "google_maps_url": "",
            "matched_project": "",
            "candidate_status": "fetch_error",
            "review_priority": "P4",
            "decision": "fetch_error",
            "market_listing_text": listing_text,
            "fetch_error": error,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

    lines = html_to_lines(raw_html)
    title = extract_h1(raw_html, fallback=listing_text)
    status = extract_status(lines)
    operator, address, description = extract_operator_address_description(title, lines)

    blob = " ".join([title, operator, address, description, listing_text])
    matched_project = match_known_project(blob, aliases)
    candidate_status, priority, decision = classify(status, matched_project, title)

    return {
        "market": clean(source.get("market")),
        "region_hint": clean(source.get("region_hint")),
        "facility_name": title,
        "operator": operator,
        "dcm_status": status,
        "address": address,
        "description": description,
        "source_url": url,
        "google_maps_url": google_maps_url(address, listing_text),
        "matched_project": matched_project,
        "candidate_status": candidate_status,
        "review_priority": priority,
        "decision": decision,
        "market_listing_text": listing_text,
        "fetch_error": "",
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    visible = [
        r for r in rows
        if clean(r.get("candidate_status")) not in {"excluded_operational", "discard_or_low_relevance"}
    ]

    counts = Counter(clean(r.get("candidate_status")) for r in rows)

    cards = "".join(
        f"""
        <div class="kpi">
          <div class="kpi-label">{e(k or "blank")}</div>
          <div class="kpi-value">{v}</div>
        </div>
        """
        for k, v in sorted(counts.items())
    )

    table_rows = []

    for r in visible:
        maps = clean(r.get("google_maps_url"))
        maps_link = f'<a class="link-pill" href="{e(maps)}" target="_blank" rel="noopener">Maps</a>' if maps else "—"

        table_rows.append(f"""
        <tr>
          <td>{e(r.get("review_priority"))}</td>
          <td>{e(r.get("candidate_status"))}</td>
          <td><strong>{e(r.get("facility_name"))}</strong><br><span class="muted">{e(r.get("operator"))}</span></td>
          <td>{e(r.get("dcm_status"))}</td>
          <td>{e(r.get("matched_project")) or "—"}</td>
          <td>{e(r.get("address")) or "—"}</td>
          <td>{maps_link}</td>
          <td><a class="link-pill" href="{e(r.get("source_url"))}" target="_blank" rel="noopener">DCM</a></td>
          <td>{e(r.get("description"))}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DataCenterMap Review</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1500px; margin:0 auto; padding:20px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:16px; }}
.kpi,.panel {{ background:white; border:1px solid #dfe4ea; border-radius:16px; box-shadow:0 8px 22px rgba(15,23,42,.07); }}
.kpi {{ padding:14px; }}
.kpi-label {{ color:#667085; font-size:11px; text-transform:uppercase; letter-spacing:.05em; }}
.kpi-value {{ margin-top:4px; font-size:26px; font-weight:800; }}
.panel {{ padding:16px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; vertical-align:top; text-align:left; }}
th {{ color:#667085; font-size:11px; text-transform:uppercase; background:#f8fafc; position:sticky; top:0; }}
a {{ color:#0f4c81; font-weight:800; text-decoration:none; }}
.link-pill {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#eff6ff; color:#0f4c81; margin:1px; }}
.muted {{ color:#667085; }}
</style>
</head>
<body>
<header>
<h1>DataCenterMap Review</h1>
<p>Review-only: esclusi gli Operational dalla vista principale. Generato il {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="kpis">
{cards}
</section>
<section class="panel">
<h2>Candidati / enrichment non operational</h2>
<table>
<thead>
<tr>
<th>Prio</th><th>Status</th><th>Facility</th><th>DCM status</th><th>Match master</th><th>Indirizzo</th><th>Maps</th><th>Fonte</th><th>Descrizione</th>
</tr>
</thead>
<tbody>
{''.join(table_rows) if table_rows else '<tr><td colspan="9">Nessun candidato non-operational.</td></tr>'}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    sources = [s for s in read_csv(SOURCES) if clean(s.get("active")).lower() == "yes"]
    master_rows = load_master_rows()
    aliases = load_aliases(master_rows)

    all_rows: list[dict[str, str]] = []

    for source in sources:
        start_url = clean(source.get("start_url"))
        print(f"[INFO] DCM market probe: {clean(source.get('market'))} -> {start_url}")

        raw_html, error = fetch(start_url)
        if error:
            print(f"[WARN] fetch failed: {error}")
            continue

        links = extract_facility_links(start_url, raw_html)
        print(f"[INFO] Facility links found: {len(links)}")

        for idx, link in enumerate(links[:MAX_FACILITIES], start=1):
            print(f"[{idx}/{min(len(links), MAX_FACILITIES)}] {link.get('market_listing_text')[:90]}")
            row = parse_facility(source, link, aliases)
            all_rows.append(row)
            time.sleep(SLEEP_SECONDS)

    fieldnames = [
        "market",
        "region_hint",
        "facility_name",
        "operator",
        "dcm_status",
        "address",
        "description",
        "source_url",
        "google_maps_url",
        "matched_project",
        "candidate_status",
        "review_priority",
        "decision",
        "market_listing_text",
        "fetch_error",
        "checked_at",
    ]

    write_csv(OUT_CSV, all_rows, fieldnames)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(all_rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(all_rows)} rows")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
