from __future__ import annotations

import csv
import html as html_lib
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


INPUT_DIR = Path("data/input/mase_search_pages")
MASE_TARGETS = Path("data/input/mase_targets.csv")
DASHBOARD = Path("data/output/italy_project_summary.csv")

OUTPUT_ALL = Path("data/output/mase_search_pages_records.csv")
OUTPUT_DC = Path("data/output/mase_search_pages_data_center_candidates.csv")
OUTPUT_TARGETS = Path("data/output/mase_search_pages_target_candidates.csv")


FALSE_POSITIVE_TERMS = [
    "idrocarburi",
    "permesso di ricerca",
    "concessione di coltivazione",
    "pozzi esplorativi",
    "arsenale",
    "disoleazione",
    "disabbiazione",
    "approdo turistico",
    "porto",
    "metanodotto",
    "eolico",
    "agrivoltaico",
    "impianto agrivoltaico",
]


KNOWN_LOCATIONS = {
    "settimo milanese": ("Settimo Milanese", "Lombardia"),
    "cornaredo": ("Cornaredo", "Lombardia"),
    "noviglio": ("Noviglio", "Lombardia"),
    "santa corinna": ("Noviglio", "Lombardia"),
    "siziano": ("Siziano", "Lombardia"),
    "lacchiarella": ("Lacchiarella", "Lombardia"),
    "segrate": ("Segrate", "Lombardia"),
    "liscate": ("Liscate", "Lombardia"),
    "melzo": ("Melzo", "Lombardia"),
    "sedriano": ("Sedriano", "Lombardia"),
    "vignate": ("Vignate", "Lombardia"),
    "vellezzo bellini": ("Vellezzo Bellini", "Lombardia"),
    "vittuone": ("Vittuone", "Lombardia"),
    "rho": ("Rho", "Lombardia"),
    "pero": ("Pero", "Lombardia"),
    "zibido san giacomo": ("Zibido San Giacomo", "Lombardia"),
    "treviglio": ("Treviglio", "Lombardia"),
    "roma": ("Roma", "Lazio"),
    "tecnopolo tiburtino": ("Roma", "Lazio"),
    "vimercate": ("Vimercate", "Lombardia"),
    "magenta": ("Magenta", "Lombardia"),
}


def clean(value: object) -> str:
    value = str(value or "")
    value = value.replace("\ufffe", "")
    value = html_lib.unescape(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value, flags=re.DOTALL)
    return clean(value)


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def docx_to_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")

    root = ET.fromstring(xml)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    parts = []
    for node in root.iter():
        if node.tag == ns + "t" and node.text:
            parts.append(node.text)
        elif node.tag == ns + "tab":
            parts.append("\t")
        elif node.tag == ns + "br":
            parts.append("\n")

    return "".join(parts).replace("\ufffe", "")


def normalize_url(url: str) -> str:
    url = html_lib.unescape(clean(url))
    if url.startswith("/"):
        return "https://va.mite.gov.it" + url
    return url


def extract_links(row_html: str) -> tuple[str, str, str, str]:
    hrefs = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', row_html, flags=re.IGNORECASE)

    info_url = ""
    doc_url = ""

    for href in hrefs:
        href = normalize_url(href)
        if "/Oggetti/Info/" in href:
            info_url = href
        elif "/Oggetti/Documentazione/" in href:
            doc_url = href

    object_id = ""
    documentation_id = ""

    m = re.search(r"/Oggetti/Info/(\d+)", info_url)
    if m:
        object_id = m.group(1)

    m = re.search(r"/Oggetti/Documentazione/(\d+)/(\d+)", doc_url)
    if m:
        documentation_id = m.group(2)

    return info_url, doc_url, object_id, documentation_id


def is_data_center_candidate(project: str, proponent: str) -> bool:
    blob = norm(project + " " + proponent)

    if any(term in blob for term in FALSE_POSITIVE_TERMS):
        return False

    return bool(re.search(r"\bdata\s*center\b|datacenter", blob, flags=re.IGNORECASE))


def infer_location_region(project: str) -> tuple[str, str]:
    low = project.lower()

    for needle, result in KNOWN_LOCATIONS.items():
        if needle in low:
            return result

    m = re.search(r"comune di ([A-ZÀ-Ùa-zà-ù' ]+)", project, flags=re.IGNORECASE)
    if m:
        return clean(m.group(1)), ""

    return "", ""


def match_score(a: str, b: str) -> int:
    aa = set(norm(a).split())
    bb = set(norm(b).split())

    if not aa or not bb:
        return 0

    score = len(aa & bb) * 10

    na = norm(a)
    nb = norm(b)

    if na and na in nb:
        score += 50
    if nb and nb in na:
        score += 50

    return score


def best_dashboard_match(project: str, proponent: str, rows: list[dict[str, str]]) -> tuple[str, int]:
    best_name = ""
    best_score = 0

    for row in rows:
        blob = " ".join(clean(v) for v in row.values())
        score = max(match_score(project, blob), match_score(proponent, blob))

        if score > best_score:
            best_score = score
            best_name = clean(row.get("project") or row.get("name") or blob[:80])

    return best_name, best_score


def parse_docx(path: Path) -> list[dict[str, str]]:
    text = docx_to_text(path)
    rows = []

    for m in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", text, flags=re.IGNORECASE | re.DOTALL):
        row_html = m.group(1)

        if "/Oggetti/Info/" not in row_html:
            continue

        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)

        if len(cells) < 3:
            continue

        project = strip_tags(cells[0])
        proponent = strip_tags(cells[1])
        procedure = strip_tags(cells[2])

        info_url, doc_url, object_id, documentation_id = extract_links(row_html)
        location, region = infer_location_region(project)

        rows.append({
            "source_file": path.name,
            "project": project,
            "proponent": proponent,
            "procedure": procedure,
            "location_guess": location,
            "region_guess": region,
            "mase_object_id": object_id,
            "source_url": info_url,
            "documentation_url": doc_url,
            "documentation_id": documentation_id,
            "is_data_center_candidate": "yes" if is_data_center_candidate(project, proponent) else "no",
        })

    return rows


def main() -> None:
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Missing input dir: {INPUT_DIR}")

    target_rows = read_csv(MASE_TARGETS)
    dashboard_rows = read_csv(DASHBOARD)

    existing_target_ids = {
        clean(r.get("mase_object_id"))
        for r in target_rows
        if clean(r.get("mase_object_id"))
    }

    all_rows = []

    for path in sorted(INPUT_DIR.glob("*.docx")):
        all_rows.extend(parse_docx(path))

    deduped = []
    seen = set()

    for row in all_rows:
        key = row.get("mase_object_id") or (row.get("project"), row.get("proponent"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    now = datetime.now().isoformat(timespec="seconds")

    for row in deduped:
        dashboard_match, dashboard_score = best_dashboard_match(
            row["project"],
            row["proponent"],
            dashboard_rows,
        )

        object_id = row.get("mase_object_id", "")

        if object_id in existing_target_ids:
            status = "already_in_mase_targets"
            priority = "P3"
        elif row.get("is_data_center_candidate") == "yes" and dashboard_score >= 50:
            status = "maybe_already_in_dashboard"
            priority = "P2"
        elif row.get("is_data_center_candidate") == "yes":
            status = "new_mase_candidate"
            priority = "P1"
        else:
            status = "discard_or_low_relevance"
            priority = "P4"

        row["candidate_status"] = status
        row["priority"] = priority
        row["dashboard_match"] = dashboard_match
        row["dashboard_match_score"] = str(dashboard_score)
        row["checked"] = "no"
        row["notes"] = ""
        row["created_at"] = now

    dc_rows = [
        r for r in deduped
        if r.get("is_data_center_candidate") == "yes"
    ]

    target_candidate_rows = [
        {
            "project": r["project"],
            "developer": r["proponent"],
            "location": r["location_guess"],
            "region": r["region_guess"],
            "mase_object_id": r["mase_object_id"],
            "source_url": r["source_url"],
            "notes": f'{r["procedure"]}; imported from MASE search page source',
        }
        for r in dc_rows
        if r.get("candidate_status") in {"new_mase_candidate", "maybe_already_in_dashboard"}
        and r.get("mase_object_id")
    ]

    OUTPUT_ALL.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "source_file",
        "project",
        "proponent",
        "procedure",
        "location_guess",
        "region_guess",
        "mase_object_id",
        "source_url",
        "documentation_url",
        "documentation_id",
        "is_data_center_candidate",
        "candidate_status",
        "priority",
        "dashboard_match",
        "dashboard_match_score",
        "checked",
        "notes",
        "created_at",
    ]

    for path, rows in [
        (OUTPUT_ALL, deduped),
        (OUTPUT_DC, dc_rows),
    ]:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[OK] Written {path} with {len(rows)} rows")

    target_fields = [
        "project",
        "developer",
        "location",
        "region",
        "mase_object_id",
        "source_url",
        "notes",
    ]

    with OUTPUT_TARGETS.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=target_fields)
        writer.writeheader()
        writer.writerows(target_candidate_rows)

    print(f"[OK] Written {OUTPUT_TARGETS} with {len(target_candidate_rows)} target candidate rows")


if __name__ == "__main__":
    main()
