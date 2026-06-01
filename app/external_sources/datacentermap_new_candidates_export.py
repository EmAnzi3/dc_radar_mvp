from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/external_sources/datacentermap_candidates_curated.csv")
MASTER_CSV = Path("data/output/dc_project_fused_master.csv")
MASTER_JSON = Path("docs/dc_project_fused_master.json")

OUT_CSV = Path("data/output/external_sources/datacentermap_new_candidates_review.csv")
OUT_HTML = Path("reports/site/external_sources/datacentermap_new_candidates_review.html")
OUT_EXCLUSIONS = Path("data/output/external_sources/datacentermap_new_candidates_exclusions.csv")


VALID_STATUSES = {
    "planned",
    "under construction",
    "land banked",
}

BAD_MARKERS = [
    "you re in the right place",
    "full capacity",
    "seriously researching data centers",
    "we love to see it",
]


FORCE_KEEP_NEW_CANDIDATES = {
    "cyrusone mil2",
    "cyrusone mil2 milan",
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


def load_master_projects() -> set[str]:
    projects: set[str] = set()

    for row in read_csv(MASTER_CSV):
        project = clean(row.get("project"))
        if project:
            projects.add(norm(project))

    if projects or not MASTER_JSON.exists():
        return projects

    try:
        data = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    except Exception:
        return projects

    rows = []

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ["records", "projects", "data", "rows"]:
            value = data.get(key)
            if isinstance(value, list):
                rows = value
                break

    for row in rows:
        if isinstance(row, dict):
            project = clean(row.get("project"))
            if project:
                projects.add(norm(project))

    return projects


def force_keep_new_candidate(row: dict[str, str]) -> bool:
    facility = norm(row.get("facility_name"))
    source_url = norm(row.get("source_url"))

    blob = f"{facility} {source_url}"

    return any(token in blob for token in FORCE_KEEP_NEW_CANDIDATES)


def is_bad_page(row: dict[str, str]) -> bool:
    blob = norm(" ".join([
        row.get("facility_name", ""),
        row.get("operator", ""),
        row.get("description", ""),
        row.get("source_url", ""),
    ]))

    return any(marker in blob for marker in BAD_MARKERS)


def is_already_known(row: dict[str, str], master_projects: set[str]) -> bool:
    facility = norm(row.get("facility_name"))

    if force_keep_new_candidate(row):
        return False

    # Esclusione solo se la facility è esattamente già un progetto master.
    if facility in master_projects:
        return True

    # Difensivo: Microsoft Bornasco era uscito come new candidate in alcuni run,
    # ma è già presente nel master.
    if facility == "microsoft bornasco":
        return True

    return False

def city_from_address(address: str) -> str:
    parts = [clean(p) for p in clean(address).split(",") if clean(p)]

    for i, part in enumerate(parts):
        if re.fullmatch(r"\d{5}", part) and i + 1 < len(parts):
            return parts[i + 1]

        m = re.search(r"\b\d{5}\b\s+(.+)", part)
        if m:
            return clean(m.group(1))

    if len(parts) >= 2:
        return parts[-2]

    return ""


def priority_rank(priority: str) -> int:
    order = {
        "P1": 1,
        "P2": 2,
        "P3": 3,
        "P4": 4,
    }

    return order.get(clean(priority), 9)


def validation_queries(row: dict[str, str], city: str) -> dict[str, str]:
    facility = clean(row.get("facility_name"))
    operator = clean(row.get("operator"))

    return {
        "query_operator_site": f'"{facility}" "{operator}" data center',
        "query_regional_via_vas": f'"{facility}" "{city}" VIA VAS "data center"',
        "query_municipality_suap": f'"{facility}" "{city}" "permesso di costruire" OR SUAP OR "albo pretorio"',
        "query_mase": f'"{facility}" site:va.mite.gov.it OR site:va.mase.gov.it',
        "query_contractor_gc": f'"{operator}" "{city}" "general contractor" OR EPC OR "impresa esecutrice"',
    }


def build_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    master_projects = load_master_projects()

    export_rows: list[dict[str, str]] = []
    exclusions: list[dict[str, str]] = []

    for row in read_csv(INPUT):
        candidate_status = clean(row.get("candidate_status"))
        dcm_status = clean(row.get("dcm_status_curated") or row.get("dcm_status"))

        if candidate_status != "new_candidate_review":
            continue

        exclusion_reason = ""

        if norm(dcm_status) not in VALID_STATUSES:
            exclusion_reason = "invalid_or_missing_status"
        elif is_bad_page(row):
            exclusion_reason = "capacity_or_interstitial_page"
        elif is_already_known(row, master_projects):
            exclusion_reason = "already_known_in_master"

        if exclusion_reason:
            exclusions.append({
                "facility_name": clean(row.get("facility_name")),
                "operator": clean(row.get("operator")),
                "dcm_status": dcm_status,
                "address": clean(row.get("address")),
                "source_url": clean(row.get("source_url")),
                "exclusion_reason": exclusion_reason,
                "matched_project": clean(row.get("matched_project_curated") or row.get("matched_project")),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        address = clean(row.get("address"))
        city = city_from_address(address)
        queries = validation_queries(row, city)

        export_rows.append({
            "review_priority": clean(row.get("review_priority")),
            "facility_name": clean(row.get("facility_name")),
            "operator": clean(row.get("operator")),
            "dcm_status": dcm_status,
            "address": address,
            "city_guess": city,
            "google_maps_url": clean(row.get("google_maps_url")),
            "source_url": clean(row.get("source_url")),
            "description": clean(row.get("description")),
            "source_confidence": "commercial_unverified",
            "next_action": "validate_with_operator_and_public_sources",
            "query_operator_site": queries["query_operator_site"],
            "query_regional_via_vas": queries["query_regional_via_vas"],
            "query_municipality_suap": queries["query_municipality_suap"],
            "query_mase": queries["query_mase"],
            "query_contractor_gc": queries["query_contractor_gc"],
            "review_decision": "",
            "notes": "",
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    export_rows = sorted(
        export_rows,
        key=lambda r: (
            priority_rank(r["review_priority"]),
            norm(r["dcm_status"]),
            norm(r["facility_name"]),
        ),
    )

    return export_rows, exclusions


def render_html(rows: list[dict[str, str]], exclusions: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    table_rows = []

    for r in rows:
        maps = clean(r.get("google_maps_url"))
        source = clean(r.get("source_url"))

        maps_link = f'<a class="link-pill" href="{e(maps)}" target="_blank" rel="noopener">Maps</a>' if maps else "—"
        source_link = f'<a class="link-pill" href="{e(source)}" target="_blank" rel="noopener">DCM</a>' if source else "—"

        table_rows.append(f"""
        <tr>
          <td>{e(r.get("review_priority"))}</td>
          <td><strong>{e(r.get("facility_name"))}</strong><br><span class="muted">{e(r.get("operator"))}</span></td>
          <td>{e(r.get("dcm_status"))}</td>
          <td>{e(r.get("address"))}<br><span class="muted">{e(r.get("city_guess"))}</span></td>
          <td>{maps_link}</td>
          <td>{source_link}</td>
          <td>{e(r.get("description"))}</td>
          <td>
            <div><strong>Operatore:</strong> {e(r.get("query_operator_site"))}</div>
            <div><strong>Regione:</strong> {e(r.get("query_regional_via_vas"))}</div>
            <div><strong>Comune:</strong> {e(r.get("query_municipality_suap"))}</div>
            <div><strong>MASE:</strong> {e(r.get("query_mase"))}</div>
            <div><strong>GC:</strong> {e(r.get("query_contractor_gc"))}</div>
          </td>
        </tr>
        """)

    exclusion_rows = []

    for r in exclusions:
        exclusion_rows.append(f"""
        <tr>
          <td>{e(r.get("facility_name"))}</td>
          <td>{e(r.get("operator"))}</td>
          <td>{e(r.get("dcm_status"))}</td>
          <td>{e(r.get("exclusion_reason"))}</td>
          <td><a class="link-pill" href="{e(r.get("source_url"))}" target="_blank" rel="noopener">DCM</a></td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DataCenterMap New Candidates Review</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1600px; margin:0 auto; padding:20px; }}
.panel {{ background:white; border:1px solid #dfe4ea; border-radius:16px; box-shadow:0 8px 22px rgba(15,23,42,.07); padding:16px; margin-bottom:18px; overflow:auto; }}
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
<h1>DataCenterMap New Candidates Review</h1>
<p>Solo nuovi candidati non-operational da validare. Generato il {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="panel">
<h2>Nuovi candidati</h2>
<table>
<thead>
<tr>
<th>Prio</th><th>Facility</th><th>Stato DCM</th><th>Indirizzo</th><th>Maps</th><th>Fonte</th><th>Descrizione</th><th>Query validazione</th>
</tr>
</thead>
<tbody>
{''.join(table_rows) if table_rows else '<tr><td colspan="8">Nessun nuovo candidato.</td></tr>'}
</tbody>
</table>
</section>

<section class="panel">
<h2>Esclusi dall'export pulito</h2>
<table>
<thead>
<tr>
<th>Facility</th><th>Operatore</th><th>Stato DCM</th><th>Motivo esclusione</th><th>Fonte</th>
</tr>
</thead>
<tbody>
{''.join(exclusion_rows) if exclusion_rows else '<tr><td colspan="5">Nessuna esclusione.</td></tr>'}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    rows, exclusions = build_rows()

    fields = [
        "review_priority",
        "facility_name",
        "operator",
        "dcm_status",
        "address",
        "city_guess",
        "google_maps_url",
        "source_url",
        "description",
        "source_confidence",
        "next_action",
        "query_operator_site",
        "query_regional_via_vas",
        "query_municipality_suap",
        "query_mase",
        "query_contractor_gc",
        "review_decision",
        "notes",
        "checked_at",
    ]

    exclusion_fields = [
        "facility_name",
        "operator",
        "dcm_status",
        "address",
        "source_url",
        "exclusion_reason",
        "matched_project",
        "checked_at",
    ]

    write_csv(OUT_CSV, rows, fields)
    write_csv(OUT_EXCLUSIONS, exclusions, exclusion_fields)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows, exclusions), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} rows")
    print(f"[OK] Written {OUT_EXCLUSIONS} with {len(exclusions)} exclusions")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
