from __future__ import annotations

import csv
import html
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/external_sources/datacentermap_promotion_draft.csv")
OUT_HTML = Path("docs/external_candidates.html")


BUCKET_LABELS = {
    "promotion_ready": "Pronti per review master",
    "near_ready": "Quasi pronti",
    "tracked_review": "Tracciati / da completare",
}

READINESS_LABELS = {
    "ready_with_gc": "Pronto con GC",
    "ready_missing_gc": "Pronto, GC da identificare",
    "partial_public_confirmation": "Conferma pubblica parziale",
    "operator_confirmed_only": "Solo operatore confermato",
    "existing_project_child_or_enrichment": "Child/enrichment progetto esistente",
    "existing_operational_reference": "Asset esistente / reference",
    "pending_validation": "Validazione pendente",
    "weak_or_no_public_evidence": "Evidenza debole",
    "not_validated": "Non validato",
}


BUCKET_ORDER = {
    "promotion_ready": 1,
    "near_ready": 2,
    "tracked_review": 3,
}

READINESS_ORDER = {
    "ready_with_gc": 1,
    "ready_missing_gc": 2,
    "partial_public_confirmation": 3,
    "operator_confirmed_only": 4,
    "existing_project_child_or_enrichment": 5,
    "existing_operational_reference": 6,
    "pending_validation": 7,
    "weak_or_no_public_evidence": 8,
    "not_validated": 9,
}


def clean(value: object) -> str:
    return str(value or "").strip()


def esc(value: object) -> str:
    return html.escape(clean(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sort_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda r: (
            BUCKET_ORDER.get(clean(r.get("draft_bucket")), 99),
            READINESS_ORDER.get(clean(r.get("readiness")), 99),
            clean(r.get("proposed_project_name")).lower(),
        ),
    )


def badge_class(value: str) -> str:
    if value == "promotion_ready":
        return "good"
    if value == "near_ready":
        return "warn"
    if value == "tracked_review":
        return "neutral"
    return "neutral"


def readiness_class(value: str) -> str:
    if value in {"ready_with_gc", "ready_missing_gc"}:
        return "good"
    if value == "partial_public_confirmation":
        return "warn"
    if value in {"operator_confirmed_only", "existing_project_child_or_enrichment", "existing_operational_reference"}:
        return "neutral"
    return "low"


def source_links_html(value: str) -> str:
    raw = clean(value)

    if not raw:
        return '<span class="muted">—</span>'

    items = []
    pos = 0

    for match in re.finditer(r"<([^<>]+)>", raw):
        label = raw[pos:match.start()].strip()
        label = label.strip("|").strip()
        url = match.group(1).strip()

        if label and url:
            items.append(
                f'<a class="source-pill" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'
            )

        pos = match.end()

    tail = raw[pos:].strip().strip("|").strip()
    if tail:
        items.append(f'<span class="source-pill">{esc(tail)}</span>')

    return " ".join(items) if items else '<span class="muted">—</span>'

def render_kpis(rows: list[dict[str, str]]) -> str:
    buckets = Counter(clean(r.get("draft_bucket")) for r in rows)
    readiness = Counter(clean(r.get("readiness")) for r in rows)

    return f"""
    <section class="kpis">
      <div class="kpi">
        <div class="kpi-label">Candidati totali</div>
        <div class="kpi-value">{len(rows)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Promotion ready</div>
        <div class="kpi-value">{buckets.get("promotion_ready", 0)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Near-ready</div>
        <div class="kpi-value">{buckets.get("near_ready", 0)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Operator only</div>
        <div class="kpi-value">{readiness.get("operator_confirmed_only", 0)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Child / enrichment</div>
        <div class="kpi-value">{readiness.get("existing_project_child_or_enrichment", 0)}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Asset esistenti</div>
        <div class="kpi-value">{readiness.get("existing_operational_reference", 0)}</div>
      </div>
    </section>
    """


def render_cards(rows: list[dict[str, str]]) -> str:
    cards = []

    for r in rows:
        name = clean(r.get("proposed_project_name"))
        bucket = clean(r.get("draft_bucket"))
        readiness = clean(r.get("readiness"))
        maps = clean(r.get("google_maps_url"))
        dcm = clean(r.get("dcm_source_url"))

        maps_link = f'<a class="link-pill" href="{esc(maps)}" target="_blank" rel="noopener">Maps</a>' if maps else ""
        dcm_link = f'<a class="link-pill" href="{esc(dcm)}" target="_blank" rel="noopener">DataCenterMap</a>' if dcm else ""

        search_blob = " ".join([
            name,
            clean(r.get("operator_or_main_subject")),
            clean(r.get("authorization_proponent")),
            clean(r.get("city")),
            bucket,
            readiness,
        ]).lower()

        cards.append(f"""
        <article class="card" data-bucket="{esc(bucket)}" data-readiness="{esc(readiness)}" data-search="{esc(search_blob)}">
          <div class="card-top">
            <div>
              <h2>{esc(name)}</h2>
              <p class="subtitle">{esc(r.get("operator_or_main_subject"))} · {esc(r.get("city"))}</p>
            </div>
            <div class="badges">
              <span class="badge {badge_class(bucket)}">{esc(BUCKET_LABELS.get(bucket, bucket))}</span>
              <span class="badge {readiness_class(readiness)}">{esc(READINESS_LABELS.get(readiness, readiness))}</span>
            </div>
          </div>

          <div class="grid">
            <div>
              <div class="label">Operatore</div>
              <div class="value">{esc(r.get("operator_or_main_subject")) or "—"}</div>
            </div>
            <div>
              <div class="label">Proponente autorizzativo</div>
              <div class="value">{esc(r.get("authorization_proponent")) or "—"}</div>
            </div>
            <div>
              <div class="label">GC / contractor</div>
              <div class="value weak">{esc(r.get("contractor_or_partner")) or "Da identificare"}</div>
            </div>
            <div>
              <div class="label">Stato DCM raw</div>
              <div class="value">{esc(r.get("dcm_status")) or "—"}</div>
            </div>
            <div>
              <div class="label">MW IT</div>
              <div class="value">{esc(r.get("it_power_mw")) or "—"}</div>
            </div>
            <div>
              <div class="label">Superficie</div>
              <div class="value">{esc(r.get("site_area_m2")) or "—"}</div>
            </div>
            <div class="wide">
              <div class="label">Indirizzo</div>
              <div class="value">{esc(r.get("address")) or "—"}</div>
              <div>{maps_link} {dcm_link}</div>
            </div>
          </div>

          <details>
            <summary>Dettaglio validazione</summary>
            <div class="details-grid">
              <div>
                <div class="label">Layer confermati</div>
                <p>{esc(r.get("confirmed_layers")) or "—"}</p>
              </div>
              <div>
                <div class="label">Layer aperti</div>
                <p>{esc(r.get("pending_layers")) or "—"}</p>
              </div>
              <div>
                <div class="label">Raccomandazione</div>
                <p>{esc(r.get("promotion_recommendation")) or "—"}</p>
              </div>
              <div>
                <div class="label">Fonti</div>
                <p>{source_links_html(r.get("source_links"))}</p>
              </div>
              <div class="wide">
                <div class="label">Facts sintetici</div>
                <p>{esc(r.get("summary_facts")) or "—"}</p>
              </div>
            </div>
          </details>
        </article>
        """)

    return "\n".join(cards)


def render_html(rows: list[dict[str, str]]) -> str:
    rows = sort_rows(rows)
    generated_at = datetime.now().isoformat(timespec="seconds")

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>External Candidates - Data Center Radar</title>
<style>
:root {{
  --bg:#f5f7fb;
  --text:#172033;
  --muted:#667085;
  --line:#dfe4ea;
  --panel:#ffffff;
  --blue:#0f4c81;
  --dark:#08111f;
  --good-bg:#ecfdf3;
  --good:#166534;
  --warn-bg:#fff7ed;
  --warn:#92400e;
  --neutral-bg:#eff6ff;
  --neutral:#0f4c81;
  --low-bg:#f1f5f9;
  --low:#475569;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}}
header {{
  background:linear-gradient(135deg,var(--dark),var(--blue));
  color:white;
  padding:26px 30px;
}}
header h1 {{ margin:0; font-size:30px; }}
header p {{ margin:8px 0 0; color:#dbeafe; }}
main {{
  max-width:1500px;
  margin:0 auto;
  padding:20px;
}}
.nav {{
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  margin-bottom:16px;
}}
.nav a {{
  color:var(--blue);
  font-weight:800;
  text-decoration:none;
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
.kpis {{
  display:grid;
  grid-template-columns:repeat(6,minmax(0,1fr));
  gap:12px;
  margin-bottom:16px;
}}
.kpi {{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:16px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:14px;
}}
.kpi-label {{
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.05em;
}}
.kpi-value {{
  margin-top:4px;
  font-size:28px;
  font-weight:900;
}}
.filters {{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:16px;
  padding:14px;
  margin-bottom:16px;
  display:grid;
  grid-template-columns:2fr 1fr 1fr;
  gap:10px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
}}
input, select {{
  width:100%;
  padding:10px 12px;
  border:1px solid #cbd5e1;
  border-radius:10px;
  font-size:14px;
}}
.card {{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:18px;
  margin-bottom:16px;
}}
.card-top {{
  display:flex;
  justify-content:space-between;
  gap:16px;
  align-items:flex-start;
  margin-bottom:16px;
}}
h2 {{ margin:0; font-size:22px; }}
.subtitle {{ margin:5px 0 0; color:var(--muted); }}
.badges {{
  display:flex;
  flex-wrap:wrap;
  gap:6px;
  justify-content:flex-end;
}}
.badge {{
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  font-weight:800;
  font-size:11px;
  white-space:nowrap;
}}
.badge.good {{ background:var(--good-bg); color:var(--good); }}
.badge.warn {{ background:var(--warn-bg); color:var(--warn); }}
.badge.neutral {{ background:var(--neutral-bg); color:var(--neutral); }}
.badge.low {{ background:var(--low-bg); color:var(--low); }}
.grid {{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin-bottom:14px;
}}
.details-grid {{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px;
  margin-top:12px;
}}
.wide {{ grid-column:1 / -1; }}
.label {{
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.05em;
  margin-bottom:4px;
}}
.value {{
  font-weight:800;
}}
.weak {{ color:var(--warn); }}
.link-pill, .source-pill {{
  display:inline-block;
  padding:4px 9px;
  border-radius:999px;
  background:var(--neutral-bg);
  color:var(--neutral);
  text-decoration:none;
  font-weight:800;
  margin:6px 4px 0 0;
  font-size:12px;
}}
.muted {{ color:var(--muted); }}
details {{
  border-top:1px solid #e5e7eb;
  padding-top:12px;
}}
summary {{
  cursor:pointer;
  color:var(--blue);
  font-weight:900;
}}
footer {{
  color:var(--muted);
  padding:20px 0;
  font-size:12px;
}}
.hidden {{ display:none; }}
@media (max-width:900px) {{
  .kpis {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
  .filters {{ grid-template-columns:1fr; }}
  .grid, .details-grid {{ grid-template-columns:1fr; }}
  .card-top {{ flex-direction:column; }}
  .badges {{ justify-content:flex-start; }}
}}
</style>
</head>
<body>
<header>
  <h1>External Candidates</h1>
  <p>Vista review candidati DataCenterMap · nessun dato applicato automaticamente al master · generato il {esc(generated_at)}</p>
</header>
<main>
  <div class="nav">
    <a href="index.html">← Torna alla dashboard principale</a>
    <span class="muted">Fonte: DataCenterMap + validazioni manuali/operatori/fonti pubbliche</span>
  </div>

  <div class="notice">
    Review only: la pagina mostra anche i candidati non promuovibili per evidenziare fino a che livello sono stati validati.
  </div>

  {render_kpis(rows)}

  <section class="filters">
    <input id="searchBox" type="search" placeholder="Cerca candidato, operatore, comune, proponente...">
    <select id="bucketFilter">
      <option value="">Tutti i bucket</option>
      <option value="promotion_ready">Promotion ready</option>
      <option value="near_ready">Near-ready</option>
      <option value="tracked_review">Tracked review</option>
    </select>
    <select id="readinessFilter">
      <option value="">Tutte le readiness</option>
      <option value="ready_missing_gc">Pronto, GC da identificare</option>
      <option value="partial_public_confirmation">Conferma pubblica parziale</option>
      <option value="operator_confirmed_only">Solo operatore confermato</option>
      <option value="existing_project_child_or_enrichment">Child/enrichment</option>
      <option value="existing_operational_reference">Asset esistente</option>
      <option value="pending_validation">Validazione pendente</option>
    </select>
  </section>

  <section id="cards">
    {render_cards(rows)}
  </section>

  <footer>
    Nota: questa pagina è una vista di review. La promozione nel master ufficiale resta manuale.
  </footer>
</main>

<script>
const searchBox = document.getElementById("searchBox");
const bucketFilter = document.getElementById("bucketFilter");
const readinessFilter = document.getElementById("readinessFilter");
const cards = Array.from(document.querySelectorAll(".card"));

function applyFilters() {{
  const q = (searchBox.value || "").toLowerCase().trim();
  const bucket = bucketFilter.value;
  const readiness = readinessFilter.value;

  cards.forEach(card => {{
    const matchesSearch = !q || (card.dataset.search || "").includes(q);
    const matchesBucket = !bucket || card.dataset.bucket === bucket;
    const matchesReadiness = !readiness || card.dataset.readiness === readiness;

    card.classList.toggle("hidden", !(matchesSearch && matchesBucket && matchesReadiness));
  }});
}}

searchBox.addEventListener("input", applyFilters);
bucketFilter.addEventListener("change", applyFilters);
readinessFilter.addEventListener("change", applyFilters);
</script>
</body>
</html>
"""


def main() -> None:
    rows = read_csv(INPUT)

    if not rows:
        raise SystemExit(f"Nessun input trovato: {INPUT}")

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    html_out = render_html(rows)
    html_out = "\n".join(line.rstrip() for line in html_out.splitlines()) + "\n"

    OUT_HTML.write_text(html_out, encoding="utf-8")

    print(f"[OK] Written {OUT_HTML} with {len(rows)} candidates")


if __name__ == "__main__":
    main()
