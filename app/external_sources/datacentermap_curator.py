from __future__ import annotations

import csv
import html
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/external_sources/datacentermap_candidates.csv")
OUT_CSV = Path("data/output/external_sources/datacentermap_candidates_curated.csv")
OUT_HTML = Path("reports/site/external_sources/datacentermap_review_curated.html")


TARGET_STATUSES = {
    "planned",
    "under construction",
    "land banked",
}

EXCLUDED_STATUSES = {
    "operational",
}


EXACT_KNOWN_MATCHES = [
    ("DATA4 Cornaredo", [r"\bDATA4 Milan Campus\b", r"\bDATA4 Milan Campus MIL01\b"]),
    ("Retelit Avalon 3", [r"\bRetelit Avalon 3\b"]),
    ("Vantage MXP2", [r"\bVantage MXP2\b"]),
    ("CyrusOne MIL1", [r"\bCyrusOne MIL1\b"]),
    ("Equinix ML7-ML8", [r"\bEquinix ML7x\b", r"\bEquinix ML7\b", r"\bEquinix ML8\b"]),
]


# Nuovi o possibili sibling da NON schiacciare su progetti esistenti.
FORCE_NEW_CANDIDATES = [
    "CyrusOne MIL2",
    "CloudHQ MXP Campus",
    "hscale MXP1",
    "VIRTUS MILAN1",
    "STACK Infrastructure MIL08B",
]


ADDRESS_OVERLAP_REVIEW = [
    "MIL01A Vaultica Data Centers",
    "MIL01 Vaultica Data Centers",
    "MOMIT SRL",
]


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


def regex_match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def exact_known_project(row: dict[str, str]) -> str:
    blob = " ".join([
        clean(row.get("facility_name")),
        clean(row.get("operator")),
        clean(row.get("address")),
        clean(row.get("description")),
        clean(row.get("market_listing_text")),
    ])

    for project, patterns in EXACT_KNOWN_MATCHES:
        if regex_match_any(blob, patterns):
            return project

    return ""


def is_forced_new(row: dict[str, str]) -> bool:
    title = clean(row.get("facility_name"))
    listing = clean(row.get("market_listing_text"))
    blob = f"{title} {listing}"

    return any(name.lower() in blob.lower() for name in FORCE_NEW_CANDIDATES)


def is_address_overlap_review(row: dict[str, str]) -> bool:
    title = clean(row.get("facility_name"))
    listing = clean(row.get("market_listing_text"))
    blob = f"{title} {listing}"

    return any(name.lower() in blob.lower() for name in ADDRESS_OVERLAP_REVIEW)


def infer_status_from_description(row: dict[str, str]) -> str:
    status = clean(row.get("dcm_status"))

    if status:
        return status

    blob = norm(" ".join([
        row.get("description", ""),
        row.get("facility_name", ""),
        row.get("market_listing_text", ""),
    ]))

    if "under construction" in blob or "begins construction" in blob:
        return "Under Construction"

    if "planned" in blob or "expected to be operational" in blob or "scheduled" in blob:
        return "Planned"

    if "land banked" in blob:
        return "Land Banked"

    return ""


def maps_precision(row: dict[str, str]) -> str:
    address = clean(row.get("address"))

    if not address:
        return "none"

    # Se contiene via + CAP/comune, è abbastanza puntuale.
    if re.search(r"\b\d{5}\b", address) and re.search(r"\b(via|viale|strada|sp|s\.p\.|piazza)\b", address, re.I):
        return "address"

    return "area"


def curate(row: dict[str, str]) -> dict[str, str]:
    status = infer_status_from_description(row)
    status_norm = norm(status)
    exact_match = exact_known_project(row)

    title = clean(row.get("facility_name"))

    if is_address_overlap_review(row):
        curated_status = "possible_duplicate_or_child_facility"
        priority = "P3"
        decision = "review_same_address_or_cluster"
        matched_project = clean(row.get("matched_project")) or "Stack Campus Siziano"

    elif is_forced_new(row) and status_norm in TARGET_STATUSES:
        curated_status = "new_candidate_review"
        priority = "P1" if status_norm in {"planned", "under construction"} else "P2"
        decision = "manual_review_new_candidate"
        matched_project = ""

    elif status_norm in EXCLUDED_STATUSES:
        curated_status = "excluded_operational"
        priority = "P4"
        decision = "exclude_operational"
        matched_project = exact_match or clean(row.get("matched_project"))

    elif exact_match and status_norm in TARGET_STATUSES:
        curated_status = "known_project_enrichment"
        priority = "P2"
        decision = "enrich_existing_project"
        matched_project = exact_match

    elif exact_match and not status_norm:
        curated_status = "known_project_enrichment"
        priority = "P3"
        decision = "enrich_existing_project_status_unknown"
        matched_project = exact_match

    elif not exact_match and status_norm in {"planned", "under construction"}:
        curated_status = "new_candidate_review"
        priority = "P1"
        decision = "manual_review_new_candidate"
        matched_project = ""

    elif not exact_match and status_norm == "land banked":
        curated_status = "new_candidate_review"
        priority = "P2"
        decision = "manual_review_land_banked"
        matched_project = ""

    elif not status_norm:
        curated_status = "status_unknown_review"
        priority = "P4"
        decision = "hide_until_status_clear"
        matched_project = exact_match or ""

    else:
        curated_status = "discard_or_low_relevance"
        priority = "P4"
        decision = "discard"
        matched_project = exact_match or clean(row.get("matched_project"))

    out = dict(row)
    out["dcm_status_curated"] = status
    out["matched_project_curated"] = matched_project
    out["candidate_status_raw"] = clean(row.get("candidate_status"))
    out["candidate_status"] = curated_status
    out["review_priority"] = priority
    out["decision"] = decision
    out["maps_precision"] = maps_precision(row)
    out["curated_at"] = datetime.now().isoformat(timespec="seconds")

    return out


def visible_in_report(row: dict[str, str]) -> bool:
    return clean(row.get("candidate_status")) in {
        "new_candidate_review",
        "known_project_enrichment",
        "possible_duplicate_or_child_facility",
    }


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    counts = Counter(clean(r.get("candidate_status")) for r in rows)
    visible = [r for r in rows if visible_in_report(r)]

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
          <td>{e(r.get("dcm_status_curated")) or "—"}</td>
          <td>{e(r.get("matched_project_curated")) or "—"}</td>
          <td>{e(r.get("address")) or "—"}<br><span class="muted">{e(r.get("maps_precision"))}</span></td>
          <td>{maps_link}</td>
          <td><a class="link-pill" href="{e(r.get("source_url"))}" target="_blank" rel="noopener">DCM</a></td>
          <td>{e(r.get("decision"))}</td>
          <td>{e(r.get("description"))}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DataCenterMap Review Curated</title>
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
<h1>DataCenterMap Review Curated</h1>
<p>Solo candidati non-operational, enrichment e possibili duplicati/child facility. Generato il {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="kpis">
{cards}
</section>
<section class="panel">
<h2>Review utile</h2>
<table>
<thead>
<tr>
<th>Prio</th><th>Status</th><th>Facility</th><th>DCM status</th><th>Match master</th><th>Indirizzo</th><th>Maps</th><th>Fonte</th><th>Decisione</th><th>Descrizione</th>
</tr>
</thead>
<tbody>
{''.join(table_rows) if table_rows else '<tr><td colspan="10">Nessun record utile.</td></tr>'}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    rows = [curate(r) for r in read_csv(INPUT)]

    if not rows:
        raise SystemExit(f"Nessun input trovato: {INPUT}")

    fieldnames = list(rows[0].keys())
    write_csv(OUT_CSV, rows, fieldnames)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} curated rows")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
