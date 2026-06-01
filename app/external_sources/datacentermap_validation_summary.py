from __future__ import annotations

import csv
import html
from collections import defaultdict
from datetime import datetime
from pathlib import Path


QUEUE = Path("data/input/external_sources/datacentermap_validation_queue.csv")

OUT_CSV = Path("data/output/external_sources/datacentermap_validation_summary.csv")
OUT_HTML = Path("reports/site/external_sources/datacentermap_validation_summary.html")


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


def readiness_for_candidate(tasks: list[dict[str, str]]) -> tuple[str, str]:
    confirmed_layers = {
        clean(t.get("validation_layer"))
        for t in tasks
        if clean(t.get("result_status")) == "confirmed"
    }

    no_direct_layers = {
        clean(t.get("validation_layer"))
        for t in tasks
        if clean(t.get("result_status")) in {"no_direct_regional_result", "no_result"}
    }

    pending_layers = {
        clean(t.get("validation_layer"))
        for t in tasks
        if clean(t.get("checked")).lower() != "yes"
    }

    has_operator = "operator_site" in confirmed_layers
    has_mase = "mase" in confirmed_layers
    has_municipality = "municipality_suap_albo" in confirmed_layers
    has_gc = "contractor_gc" in confirmed_layers

    if has_operator and has_mase and has_municipality and has_gc:
        return "ready_with_gc", "Promuovibile: progetto, fonte pubblica locale/nazionale e GC confermati."

    if has_operator and has_mase and has_municipality:
        return "ready_missing_gc", "Promuovibile in draft: progetto confermato; GC/contractor ancora da identificare."

    if has_operator and (has_mase or has_municipality):
        return "partial_public_confirmation", "Buona conferma, ma serve completare layer pubblico o locale."

    if has_operator:
        return "operator_confirmed_only", "Confermato dall'operatore; servono fonti pubbliche."

    if pending_layers:
        return "pending_validation", "Validazione incompleta."

    if no_direct_layers:
        return "weak_or_no_public_evidence", "Fonti pubbliche non trovate o insufficienti."

    return "not_validated", "Nessuna conferma utile."


def build_rows() -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in read_csv(QUEUE):
        grouped[clean(row.get("facility_name"))].append(row)

    out = []

    for facility, tasks in grouped.items():
        first = tasks[0]
        readiness, recommendation = readiness_for_candidate(tasks)

        confirmed = [
            clean(t.get("validation_layer"))
            for t in tasks
            if clean(t.get("result_status")) == "confirmed"
        ]

        pending = [
            clean(t.get("validation_layer"))
            for t in tasks
            if clean(t.get("checked")).lower() != "yes"
        ]

        facts = []

        for t in tasks:
            if clean(t.get("extracted_facts")):
                facts.append(f"{clean(t.get('validation_layer'))}: {clean(t.get('extracted_facts'))}")

        out.append({
            "facility_name": facility,
            "operator": clean(first.get("operator")),
            "dcm_status": clean(first.get("dcm_status")),
            "review_priority": clean(first.get("review_priority")),
            "city_guess": clean(first.get("city_guess")),
            "address": clean(first.get("address")),
            "google_maps_url": clean(first.get("google_maps_url")),
            "dcm_source_url": clean(first.get("dcm_source_url")),
            "confirmed_layers": " | ".join(confirmed),
            "pending_layers": " | ".join(pending),
            "readiness": readiness,
            "recommendation": recommendation,
            "summary_facts": " || ".join(facts),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        })

    order = {
        "ready_with_gc": 1,
        "ready_missing_gc": 2,
        "partial_public_confirmation": 3,
        "operator_confirmed_only": 4,
        "pending_validation": 5,
        "weak_or_no_public_evidence": 6,
        "not_validated": 7,
    }

    return sorted(out, key=lambda r: (order.get(r["readiness"], 9), r["facility_name"]))


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    table_rows = []

    for r in rows:
        maps = clean(r.get("google_maps_url"))
        dcm = clean(r.get("dcm_source_url"))

        maps_link = f'<a class="link-pill" href="{e(maps)}" target="_blank" rel="noopener">Maps</a>' if maps else "—"
        dcm_link = f'<a class="link-pill" href="{e(dcm)}" target="_blank" rel="noopener">DCM</a>' if dcm else "—"

        table_rows.append(f"""
        <tr>
          <td><strong>{e(r.get("facility_name"))}</strong><br><span class="muted">{e(r.get("operator"))}</span></td>
          <td>{e(r.get("dcm_status"))}</td>
          <td>{e(r.get("city_guess"))}<br><span class="muted">{e(r.get("address"))}</span><br>{maps_link} {dcm_link}</td>
          <td><span class="badge">{e(r.get("readiness"))}</span></td>
          <td>{e(r.get("confirmed_layers")) or "—"}</td>
          <td>{e(r.get("pending_layers")) or "—"}</td>
          <td>{e(r.get("recommendation"))}</td>
          <td>{e(r.get("summary_facts"))}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DataCenterMap Validation Summary</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1700px; margin:0 auto; padding:20px; }}
.panel {{ background:white; border:1px solid #dfe4ea; border-radius:16px; box-shadow:0 8px 22px rgba(15,23,42,.07); padding:16px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; vertical-align:top; text-align:left; }}
th {{ color:#667085; font-size:11px; text-transform:uppercase; background:#f8fafc; position:sticky; top:0; }}
a {{ color:#0f4c81; font-weight:800; text-decoration:none; }}
.link-pill {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#eff6ff; color:#0f4c81; margin:1px; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#eef2ff; color:#3730a3; font-weight:800; font-size:11px; }}
.muted {{ color:#667085; }}
</style>
</head>
<body>
<header>
<h1>DataCenterMap Validation Summary</h1>
<p>Riepilogo readiness candidati DataCenterMap. Generato il {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="panel">
<table>
<thead>
<tr>
<th>Candidato</th><th>Stato DCM</th><th>Ubicazione</th><th>Readiness</th><th>Layer confermati</th><th>Layer aperti</th><th>Raccomandazione</th><th>Facts</th>
</tr>
</thead>
<tbody>
{''.join(table_rows) if table_rows else '<tr><td colspan="8">Nessun candidato.</td></tr>'}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    rows = build_rows()

    fields = [
        "facility_name",
        "operator",
        "dcm_status",
        "review_priority",
        "city_guess",
        "address",
        "google_maps_url",
        "dcm_source_url",
        "confirmed_layers",
        "pending_layers",
        "readiness",
        "recommendation",
        "summary_facts",
        "updated_at",
    ]

    write_csv(OUT_CSV, rows, fields)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} rows")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
