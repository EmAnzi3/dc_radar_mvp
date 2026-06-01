from __future__ import annotations

import csv
import html
import re
from datetime import datetime
from pathlib import Path


SUMMARY = Path("data/output/external_sources/datacentermap_validation_summary.csv")
QUEUE = Path("data/input/external_sources/datacentermap_validation_queue.csv")

OUT_CSV = Path("data/output/external_sources/datacentermap_promotion_draft.csv")
OUT_HTML = Path("reports/site/external_sources/datacentermap_promotion_draft.html")


PROMOTABLE_READINESS = {
    "ready_with_gc",
    "ready_missing_gc",
}

NEAR_READY_READINESS = {
    "partial_public_confirmation",
}

TRACKED_READINESS = {
    "operator_confirmed_only",
    "existing_project_child_or_enrichment",
    "pending_validation",
    "weak_or_no_public_evidence",
    "not_validated",
}


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


def tasks_for_facility(queue_rows: list[dict[str, str]], facility_name: str) -> list[dict[str, str]]:
    return [
        r for r in queue_rows
        if clean(r.get("facility_name")) == facility_name
    ]


def confirmed_tasks(tasks: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        t for t in tasks
        if clean(t.get("result_status")) == "confirmed"
    ]


def source_links(tasks: list[dict[str, str]]) -> str:
    parts = []

    for t in confirmed_tasks(tasks):
        title = clean(t.get("result_title")) or clean(t.get("validation_layer"))
        url = clean(t.get("result_url"))

        if not url:
            continue

        value = f"{title} <{url}>"
        if value not in parts:
            parts.append(value)

    return " | ".join(parts)


def extract_authorization_proponent(summary_facts: str) -> str:
    facts = clean(summary_facts)

    # Casi noti: evita che gli acronimi societari con punti vengano troncati.
    known_proponents = [
        "NAMIRA S.G.R.P.A.",
        "NAMIRA SGRPA",
        "VDC MXP 11 S.r.l.",
        "VDC MXP 11 Srl",
        "VDC MXP 11 S.R.L.",
        "Retelit Datacenter S.r.l.",
        "Retelit Datacenter Srl",
        "Retelit Datacenter S.R.L.",
        "Infrastructure Italia Land 4 S.r.l.",
        "INFRASTRUCTURE ITALIA LAND 4 S.r.l.",
        "Infrastructure Italia Land 4 Srl",
        "INFRASTRUCTURE ITALIA LAND 4 S.R.L.",
    ]

    upper_facts = facts.upper()
    for proponent in known_proponents:
        if proponent.upper() in upper_facts:
            return proponent

    patterns = [
        r"\bproponent\s+(.+?)(?:\s+This confirms|\s*\|\||$)",
        r"\bproponente\s+(.+?)(?:\s+This confirms|\s*\|\||$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, facts, re.I)
        if m:
            value = clean(m.group(1))
            value = re.sub(r"\s+", " ", value)
            return value.rstrip(" .;,")

    return ""

def format_mw_value(value: str) -> str:
    value = clean(value)

    # Formato italiano solo per decimali: 13.6 -> 13,6
    if "." in value and value.count(".") == 1:
        left, right = value.split(".", 1)
        if left.isdigit() and right.isdigit():
            return f"{left},{right}"

    return value


def extract_it_power(summary_facts: str) -> str:
    # Preferisce il totale, se presente.
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*MW\s+total\s+critical\s+IT\s+load",
        r"(\d+(?:[.,]\d+)?)\s*MW\s+IT\s+load",
        r"(\d+(?:[.,]\d+)?)\s*MW",
    ]

    for pattern in patterns:
        m = re.search(pattern, summary_facts, re.I)
        if m:
            value = clean(m.group(1)).replace(",", ".")
            if value.endswith(".0"):
                value = value[:-2]
            value = format_mw_value(value)
            return f"{value} MW"

    return ""


def format_int_it(value: float) -> str:
    return f"{round(value):,}".replace(",", ".")


def normalize_area_number(raw: str) -> str:
    raw = clean(raw)

    # 204,387 -> 204.387
    # 48,000  -> 48.000
    if "," in raw and "." not in raw:
        raw = raw.replace(",", ".")

    return raw


def numeric_value(raw: str) -> float:
    raw = clean(raw)

    # 204,387 / 48,000 / 71,364 -> 204387 / 48000 / 71364
    if "," in raw and "." not in raw:
        return float(raw.replace(",", ""))

    return float(raw.replace(",", "."))


def extract_area_m2(summary_facts: str) -> str:
    facts = clean(summary_facts)

    # 1) Preferisci valori già espressi in metri quadrati.
    sqm_patterns = [
        r"(\d[\d,.]*)\s*m²",
        r"(\d[\d,.]*)\s*square\s+meters",
        r"(\d[\d,.]*)\s*sq\s*m",
        r"(\d[\d,.]*)\s*sqm",
    ]

    for pattern in sqm_patterns:
        m = re.search(pattern, facts, re.I)
        if m:
            return f"{normalize_area_number(m.group(1))} m²"

    # 2) Acres -> solo m².
    acre_patterns = [
        r"(\d[\d,.]*)\s*[-–—]?\s*acres?",
        r"(\d[\d,.]*)\s*[-–—]?\s*acre\b",
    ]

    for pattern in acre_patterns:
        m = re.search(pattern, facts, re.I)
        if m:
            acres = numeric_value(m.group(1))
            sqm = acres * 4046.8564224
            return f"{format_int_it(sqm)} m²"

    # 3) Square feet -> solo m².
    sqft_patterns = [
        r"(\d[\d,.]*)\s*square\s+feet",
        r"(\d[\d,.]*)\s*sq\s*ft",
        r"(\d[\d,.]*)\s*sqft",
    ]

    for pattern in sqft_patterns:
        m = re.search(pattern, facts, re.I)
        if m:
            sqft = numeric_value(m.group(1))
            sqm = sqft * 0.09290304
            return f"{format_int_it(sqm)} m²"

    return ""

def build_rows() -> list[dict[str, str]]:
    summary_rows = read_csv(SUMMARY)
    queue_rows = read_csv(QUEUE)

    out = []
    now = datetime.now().isoformat(timespec="seconds")

    for s in summary_rows:
        readiness = clean(s.get("readiness"))

        if (
            readiness not in PROMOTABLE_READINESS
            and readiness not in NEAR_READY_READINESS
            and readiness not in TRACKED_READINESS
        ):
            continue

        facility = clean(s.get("facility_name"))
        tasks = tasks_for_facility(queue_rows, facility)
        facts = clean(s.get("summary_facts"))

        operator = clean(s.get("operator"))
        authorization_proponent = extract_authorization_proponent(facts)

        if not authorization_proponent:
            authorization_proponent = "Da verificare"

        contractor = "Da identificare"
        if readiness == "ready_with_gc":
            contractor = "Da estrarre da layer GC confermato"

        out.append({
            "facility_name": facility,
            "proposed_project_name": facility,
            "operator_or_main_subject": operator,
            "authorization_proponent": authorization_proponent,
            "contractor_or_partner": contractor,
            "dcm_status": clean(s.get("dcm_status")),
            "city": clean(s.get("city_guess")),
            "address": clean(s.get("address")),
            "google_maps_url": clean(s.get("google_maps_url")),
            "dcm_source_url": clean(s.get("dcm_source_url")),
            "it_power_mw": extract_it_power(facts),
            "site_area_m2": extract_area_m2(facts),
            "confirmed_layers": clean(s.get("confirmed_layers")),
            "pending_layers": clean(s.get("pending_layers")),
            "readiness": readiness,
            "promotion_recommendation": clean(s.get("recommendation")),
            "source_links": source_links(tasks),
            "summary_facts": facts,
            "apply_to_master": "no",
            "draft_bucket": (
                "promotion_ready" if readiness in PROMOTABLE_READINESS
                else "near_ready" if readiness in NEAR_READY_READINESS
                else "tracked_review"
            ),
            "review_decision": "",
            "notes": "Draft only. No automatic homepage/master promotion.",
            "created_at": now,
        })

    return out


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    cards = []

    for r in rows:
        maps = clean(r.get("google_maps_url"))
        dcm = clean(r.get("dcm_source_url"))

        maps_link = f'<a class="link-pill" href="{e(maps)}" target="_blank" rel="noopener">Google Maps</a>' if maps else ""
        dcm_link = f'<a class="link-pill" href="{e(dcm)}" target="_blank" rel="noopener">DataCenterMap</a>' if dcm else ""

        source_items = []
        for source in clean(r.get("source_links")).split(" | "):
            source = clean(source)
            if not source:
                continue

            m = re.match(r"(.+?)\s+<(.+)>$", source)
            if m:
                label = e(m.group(1))
                url = e(m.group(2))
                source_items.append(f'<li><a href="{url}" target="_blank" rel="noopener">{label}</a></li>')
            else:
                source_items.append(f"<li>{e(source)}</li>")

        cards.append(f"""
        <article class="card">
          <div class="card-head">
            <div>
              <h2>{e(r.get("proposed_project_name"))}</h2>
              <p class="muted">{e(r.get("operator_or_main_subject"))} · {e(r.get("city"))}</p>
            </div>
            <span class="badge">{e(r.get("readiness"))}</span>
            <span class="badge secondary">{e(r.get("draft_bucket"))}</span>
          </div>

          <div class="grid">
            <div><div class="label">Operatore commerciale</div><div class="value">{e(r.get("operator_or_main_subject"))}</div></div>
            <div><div class="label">Proponente autorizzativo</div><div class="value">{e(r.get("authorization_proponent"))}</div></div>
            <div><div class="label">GC / contractor</div><div class="value weak">{e(r.get("contractor_or_partner"))}</div></div>
            <div><div class="label">Stato</div><div class="value">{e(r.get("dcm_status"))}</div></div>
            <div><div class="label">MW IT</div><div class="value">{e(r.get("it_power_mw")) or "—"}</div></div>
            <div><div class="label">Superficie</div><div class="value">{e(r.get("site_area_m2")) or "—"}</div></div>
            <div class="wide"><div class="label">Indirizzo</div><div class="value">{e(r.get("address"))}</div>{maps_link} {dcm_link}</div>
          </div>

          <div class="section">
            <div class="label">Layer confermati</div>
            <p>{e(r.get("confirmed_layers"))}</p>
          </div>

          <div class="section">
            <div class="label">Layer aperti</div>
            <p>{e(r.get("pending_layers")) or "—"}</p>
          </div>

          <div class="section">
            <div class="label">Raccomandazione</div>
            <p>{e(r.get("promotion_recommendation"))}</p>
          </div>

          <div class="section">
            <div class="label">Fonti confermate</div>
            <ul>{''.join(source_items) if source_items else '<li>—</li>'}</ul>
          </div>

          <div class="section">
            <div class="label">Facts</div>
            <p>{e(r.get("summary_facts"))}</p>
          </div>
        </article>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>DataCenterMap Candidate Review</title>
<style>
body {{
  margin:0;
  font-family:Arial,sans-serif;
  background:#f5f7fb;
  color:#172033;
}}
header {{
  background:linear-gradient(135deg,#08111f,#0f4c81);
  color:white;
  padding:24px 30px;
}}
main {{
  max-width:1400px;
  margin:0 auto;
  padding:20px;
}}
.notice {{
  background:#fff7ed;
  border:1px solid #fed7aa;
  color:#92400e;
  border-radius:14px;
  padding:12px 14px;
  margin-bottom:16px;
  font-weight:700;
}}
.card {{
  background:white;
  border:1px solid #dfe4ea;
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:18px;
  margin-bottom:18px;
}}
.card-head {{
  display:flex;
  justify-content:space-between;
  gap:16px;
  align-items:flex-start;
  margin-bottom:16px;
}}
h1,h2 {{ margin:0; }}
.muted {{ color:#667085; }}
.grid {{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin-bottom:16px;
}}
.wide {{ grid-column:span 3; }}
.label {{
  color:#667085;
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.05em;
  margin-bottom:4px;
}}
.value {{
  font-weight:800;
}}
.weak {{
  color:#92400e;
}}
.badge {{
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  background:#eef2ff;
  color:#3730a3;
  font-weight:800;
  font-size:11px;
}}
.link-pill {{
  display:inline-block;
  padding:4px 9px;
  border-radius:999px;
  background:#eff6ff;
  color:#0f4c81;
  text-decoration:none;
  font-weight:800;
  margin:6px 4px 0 0;
}}
.section {{
  border-top:1px solid #e5e7eb;
  padding-top:12px;
  margin-top:12px;
}}
a {{ color:#0f4c81; font-weight:800; text-decoration:none; }}
</style>
</head>
<body>
<header>
<h1>DataCenterMap Candidate Review</h1>
<p>Vista generale candidati DataCenterMap: promuovibili, near-ready, operator-only, child/enrichment. Nessun dato applicato al master. Generato il {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<div class="notice">Review only: questa vista mostra anche fin dove siamo arrivati nella validazione, non solo cosa è promuovibile.</div>
{''.join(cards) if cards else '<div class="notice">Nessun candidato promuovibile in draft.</div>'}
</main>
</body>
</html>
"""


def main() -> None:
    rows = build_rows()

    fields = [
        "facility_name",
        "proposed_project_name",
        "operator_or_main_subject",
        "authorization_proponent",
        "contractor_or_partner",
        "dcm_status",
        "city",
        "address",
        "google_maps_url",
        "dcm_source_url",
        "it_power_mw",
        "site_area_m2",
        "confirmed_layers",
        "pending_layers",
        "readiness",
        "promotion_recommendation",
        "source_links",
        "summary_facts",
        "apply_to_master",
        "draft_bucket",
        "review_decision",
        "notes",
        "created_at",
    ]

    write_csv(OUT_CSV, rows, fields)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} draft promotions")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
