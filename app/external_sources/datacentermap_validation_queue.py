from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus


INPUT = Path("data/output/external_sources/datacentermap_new_candidates_review.csv")

OUT_CSV = Path("data/input/external_sources/datacentermap_validation_queue.csv")
OUT_HTML = Path("reports/site/external_sources/datacentermap_validation_queue.html")


VALIDATION_LAYERS = [
    {
        "validation_layer": "operator_site",
        "source_level": "company",
        "source_name_field": "operator",
        "query_field": "query_operator_site",
        "purpose": "Verificare se il progetto è citato dal sito dell'operatore o da sue pagine ufficiali.",
    },
    {
        "validation_layer": "regional_via_vas",
        "source_level": "regional_authority",
        "source_name": "Regione Lombardia / VIA / VAS",
        "query_field": "query_regional_via_vas",
        "purpose": "Cercare evidenze regionali VIA, VAS, PAUR o procedimenti ambientali.",
    },
    {
        "validation_layer": "municipality_suap_albo",
        "source_level": "municipality",
        "source_name_field": "city_guess",
        "query_field": "query_municipality_suap",
        "purpose": "Cercare permessi, SUAP, albo pretorio, conferenze servizi o commissioni locali.",
    },
    {
        "validation_layer": "mase",
        "source_level": "national_authority",
        "source_name": "MASE",
        "query_field": "query_mase",
        "purpose": "Verificare eventuale presenza su portale VIA/VAS MASE.",
    },
    {
        "validation_layer": "contractor_gc",
        "source_level": "contractor_gc",
        "source_name": "GC / contractor / EPC",
        "query_field": "query_contractor_gc",
        "purpose": "Cercare general contractor, EPC, impresa esecutrice, progettisti o partner tecnici.",
    },
]


PRESERVED_FIELDS = [
    "checked",
    "result_status",
    "result_url",
    "result_title",
    "evidence_type",
    "extracted_facts",
    "next_action",
    "notes",
]


def clean(value: object) -> str:
    return str(value or "").strip()


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


def google_search_url(query: str) -> str:
    query = clean(query)
    if not query:
        return ""

    return "https://www.google.com/search?q=" + quote_plus(query)


def queue_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        clean(row.get("facility_name")),
        clean(row.get("validation_layer")),
        clean(row.get("query")),
    )


def load_existing_queue() -> dict[tuple[str, str, str], dict[str, str]]:
    existing = {}

    for row in read_csv(OUT_CSV):
        existing[queue_key(row)] = row

    return existing


def source_name_for_layer(candidate: dict[str, str], layer: dict[str, str]) -> str:
    if clean(layer.get("source_name")):
        return clean(layer.get("source_name"))

    field = clean(layer.get("source_name_field"))
    if field:
        return clean(candidate.get(field))

    return ""


def build_rows() -> list[dict[str, str]]:
    candidates = read_csv(INPUT)
    existing = load_existing_queue()

    rows: list[dict[str, str]] = []
    rank = 1
    now = datetime.now().isoformat(timespec="seconds")

    for candidate in candidates:
        for layer in VALIDATION_LAYERS:
            query = clean(candidate.get(layer["query_field"]))

            if not query:
                continue

            row = {
                "rank": str(rank),
                "facility_name": clean(candidate.get("facility_name")),
                "operator": clean(candidate.get("operator")),
                "dcm_status": clean(candidate.get("dcm_status")),
                "review_priority": clean(candidate.get("review_priority")),
                "city_guess": clean(candidate.get("city_guess")),
                "address": clean(candidate.get("address")),
                "google_maps_url": clean(candidate.get("google_maps_url")),
                "dcm_source_url": clean(candidate.get("source_url")),
                "validation_layer": clean(layer.get("validation_layer")),
                "source_level": clean(layer.get("source_level")),
                "source_name": source_name_for_layer(candidate, layer),
                "query": query,
                "search_url": google_search_url(query),
                "purpose": clean(layer.get("purpose")),
                "checked": "no",
                "result_status": "",
                "result_url": "",
                "result_title": "",
                "evidence_type": "",
                "extracted_facts": "",
                "next_action": "",
                "notes": "",
                "created_at": now,
                "updated_at": now,
            }

            previous = existing.get(queue_key(row))
            if previous:
                for field in PRESERVED_FIELDS:
                    row[field] = clean(previous.get(field))
                row["created_at"] = clean(previous.get("created_at")) or now
                row["updated_at"] = now

            rows.append(row)
            rank += 1

    return rows


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    table_rows = []

    for r in rows:
        search_url = clean(r.get("search_url"))
        maps_url = clean(r.get("google_maps_url"))
        dcm_url = clean(r.get("dcm_source_url"))

        search_link = f'<a class="link-pill" href="{e(search_url)}" target="_blank" rel="noopener">Search</a>' if search_url else "—"
        maps_link = f'<a class="link-pill" href="{e(maps_url)}" target="_blank" rel="noopener">Maps</a>' if maps_url else "—"
        dcm_link = f'<a class="link-pill" href="{e(dcm_url)}" target="_blank" rel="noopener">DCM</a>' if dcm_url else "—"

        checked = e(r.get("checked"))
        checked_class = "checked-yes" if checked.lower() == "yes" else "checked-no"

        table_rows.append(f"""
        <tr>
          <td>{e(r.get("rank"))}</td>
          <td>
            <strong>{e(r.get("facility_name"))}</strong><br>
            <span class="muted">{e(r.get("operator"))}</span><br>
            <span class="mini">{e(r.get("dcm_status"))}</span>
          </td>
          <td>{e(r.get("review_priority"))}</td>
          <td>
            {e(r.get("address"))}<br>
            <span class="muted">{e(r.get("city_guess"))}</span><br>
            {maps_link} {dcm_link}
          </td>
          <td>
            <strong>{e(r.get("validation_layer"))}</strong><br>
            <span class="muted">{e(r.get("source_name"))}</span>
          </td>
          <td>{e(r.get("query"))}<br>{search_link}</td>
          <td>{e(r.get("purpose"))}</td>
          <td><span class="{checked_class}">{checked}</span></td>
          <td>{e(r.get("result_status"))}</td>
          <td>{e(r.get("extracted_facts"))}</td>
          <td>{e(r.get("next_action"))}</td>
        </tr>
        """)

    total = len(rows)
    checked = sum(1 for r in rows if clean(r.get("checked")).lower() == "yes")
    pending = total - checked

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DataCenterMap Validation Queue</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1700px; margin:0 auto; padding:20px; }}
.kpis {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-bottom:16px; }}
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
.mini {{ display:inline-block; margin-top:3px; padding:2px 6px; border-radius:999px; background:#eef2ff; color:#3730a3; font-size:10px; font-weight:800; }}
.checked-yes {{ color:#166534; font-weight:800; }}
.checked-no {{ color:#92400e; font-weight:800; }}
</style>
</head>
<body>
<header>
<h1>DataCenterMap Validation Queue</h1>
<p>Code di verifica per i nuovi candidati non-operational DataCenterMap. Generato il {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="kpis">
  <div class="kpi"><div class="kpi-label">Task totali</div><div class="kpi-value">{total}</div></div>
  <div class="kpi"><div class="kpi-label">Verificati</div><div class="kpi-value">{checked}</div></div>
  <div class="kpi"><div class="kpi-label">Da fare</div><div class="kpi-value">{pending}</div></div>
</section>

<section class="panel">
<h2>Queue</h2>
<table>
<thead>
<tr>
<th>#</th>
<th>Candidato</th>
<th>Prio</th>
<th>Ubicazione</th>
<th>Layer</th>
<th>Query</th>
<th>Scopo</th>
<th>Checked</th>
<th>Esito</th>
<th>Facts estratti</th>
<th>Next action</th>
</tr>
</thead>
<tbody>
{''.join(table_rows) if table_rows else '<tr><td colspan="11">Nessun task.</td></tr>'}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    rows = build_rows()

    fieldnames = [
        "rank",
        "facility_name",
        "operator",
        "dcm_status",
        "review_priority",
        "city_guess",
        "address",
        "google_maps_url",
        "dcm_source_url",
        "validation_layer",
        "source_level",
        "source_name",
        "query",
        "search_url",
        "purpose",
        "checked",
        "result_status",
        "result_url",
        "result_title",
        "evidence_type",
        "extracted_facts",
        "next_action",
        "notes",
        "created_at",
        "updated_at",
    ]

    write_csv(OUT_CSV, rows, fieldnames)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} validation tasks")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
