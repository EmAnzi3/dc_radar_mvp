from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


INPUT = Path("data/output/dc_project_fused_master.csv")

DOCS_INDEX = Path("docs/index.html")
DOCS_LEGACY = Path("docs/dc_pipeline.html")
REPORTS_INDEX = Path("reports/site/index.html")
REPORTS_LEGACY = Path("reports/site/dc_pipeline.html")
JSON_OUT = Path("docs/dc_project_fused_master.json")

DOCS_PROJECTS_DIR = Path("docs/projects")
REPORTS_PROJECTS_DIR = Path("reports/site/projects")


def clean(value: object) -> str:
    return str(value or "").strip()


def esc(value: object) -> str:
    return html.escape(clean(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def split_multi(value: object) -> list[str]:
    value = clean(value)

    if not value:
        return []

    parts = []

    for token in value.replace(" || ", " | ").split("|"):
        token = clean(token)
        if token and token not in parts:
            parts.append(token)

    return parts


def slugify(value: object) -> str:
    value = clean(value).lower()
    value = value.replace("à", "a").replace("è", "e").replace("é", "e")
    value = value.replace("ì", "i").replace("ò", "o").replace("ù", "u")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "project"


def project_href(row: dict[str, str]) -> str:
    return f"projects/{slugify(row.get('project'))}.html"


def value_or_dash(value: object) -> str:
    value = clean(value)
    return esc(value) if value else "—"


def format_number(value: str) -> str:
    value = clean(value)

    if not value:
        return "—"

    parts = split_multi(value)
    formatted = []

    for part in parts:
        raw = clean(part)

        try:
            if "." in raw:
                n = float(raw)
                if n.is_integer():
                    formatted.append(f"{int(n):,}".replace(",", "."))
                else:
                    formatted.append(str(n).replace(".", ","))
            else:
                formatted.append(f"{int(raw):,}".replace(",", "."))
        except Exception:
            formatted.append(raw)

    return esc(" | ".join(formatted))


def format_mw(value: str) -> str:
    value = clean(value)

    if not value:
        return "—"

    parts = split_multi(value)
    out = []

    for part in parts:
        part = clean(part)
        try:
            n = float(part.replace(",", "."))
            if n.is_integer():
                out.append(f"{int(n):,}".replace(",", "."))
            else:
                out.append(str(n).replace(".", ","))
        except Exception:
            out.append(part)

    return esc(" | ".join(out))


def first_url(value: object) -> str:
    urls = split_multi(value)
    return urls[0] if urls else ""


def limited_urls(value: object, limit: int = 2) -> list[str]:
    urls = []

    for url in split_multi(value):
        if url and url not in urls:
            urls.append(url)

    return urls[:limit]


def label_for_url(url: str, fallback: str = "Fonte") -> str:
    url = clean(url)

    if not url:
        return fallback

    host = urlparse(url).netloc.lower().replace("www.", "")

    if "va.mite.gov.it" in host:
        return "MASE"
    if "techbau" in host:
        return "Techbau"
    if "generaleprefabbricati" in host:
        return "Gen. Prefabbricati"
    if "dbagroup" in host:
        return "DBA Group"
    if "a2acalore" in host:
        return "A2A Calore"
    if "mercuryeng" in host:
        return "Mercury"
    if host:
        return host.split(".")[0].title()

    return fallback


def link_pill(url: str, label: str) -> str:
    return f'<a class="link-pill" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def compact_sources(row: dict[str, str]) -> str:
    items = []

    mase_url = first_url(row.get("mase_source_urls"))
    if mase_url:
        items.append(link_pill(mase_url, "MASE"))

    for url in limited_urls(row.get("contractor_source_urls"), 2):
        label = label_for_url(url, "Fonte")
        item = link_pill(url, label)
        if item not in items:
            items.append(item)

    if len(items) == 1:
        for url in limited_urls(row.get("mw_it_source_urls"), 1):
            label = label_for_url(url, "MW IT")
            item = link_pill(url, label)
            if item not in items:
                items.append(item)

    if not items:
        return '<span class="muted">—</span>'

    return " ".join(items[:3])


def all_sources(row: dict[str, str]) -> str:
    groups = [
        ("MASE", row.get("mase_source_urls")),
        ("Contractor / partner", row.get("contractor_source_urls")),
        ("MW IT", row.get("mw_it_source_urls")),
        ("MWt", row.get("thermal_mwt_source_urls")),
        ("Superficie", row.get("site_area_source_urls")),
    ]

    html_blocks = []

    for label, urls_raw in groups:
        urls = limited_urls(urls_raw, 6)
        if not urls:
            continue

        links = " ".join(link_pill(url, label_for_url(url, label)) for url in urls)
        html_blocks.append(f"<div><strong>{esc(label)}:</strong> {links}</div>")

    if not html_blocks:
        return '<span class="muted">—</span>'

    return "".join(html_blocks)


def badge(text: str, cls: str, title: str = "") -> str:
    title_attr = f' title="{esc(title)}"' if title else ""
    return f'<span class="badge {esc(cls)}"{title_attr}>{esc(text)}</span>'


def confidence_badge(value: object) -> str:
    value = clean(value)

    if not value:
        return ""

    try:
        score = int(float(value.replace(",", ".")))
    except Exception:
        score = 0

    if score >= 90:
        cls = "conf-high"
    elif score >= 70:
        cls = "conf-mid"
    else:
        cls = "conf-low"

    return (
        f'<span class="confidence {cls}" '
        f'title="Affidabilità della fonte contractor/partner: {esc(value)}%">'
        f'Aff. {esc(value)}%</span>'
    )


def status_badge(row: dict[str, str]) -> str:
    status = clean(row.get("business_status"))

    label_map = {
        "Consolidato": "OK",
        "Da verificare": "Verifica",
        "Parziale": "Parziale",
        "Fonti esterne necessarie": "Fonti ext.",
        "Debole": "Debole",
    }

    title_map = {
        "Consolidato": "Dati principali coerenti e già usabili.",
        "Da verificare": "Dato chiave presente, ma da verificare su fonte primaria.",
        "Parziale": "Progetto valido, ma mancano dati importanti.",
        "Fonti esterne necessarie": "MASE assente o insufficiente: servono fonti aziendali, GC, enti locali o altre fonti.",
        "Debole": "Informazione ancora debole o incompleta.",
    }

    cls = {
        "Consolidato": "grade-a",
        "Da verificare": "grade-b",
        "Parziale": "grade-c",
        "Fonti esterne necessarie": "grade-d",
        "Debole": "grade-d",
    }.get(status, "grade-d")

    label = label_map.get(status, "Da classificare")
    title = title_map.get(status, "Qualità dato non classificata.")

    return badge(label, cls, title)


def priority_badge(row: dict[str, str]) -> str:
    priority = clean(row.get("business_priority"))

    cls = {
        "Alta": "priority-high",
        "Media": "priority-mid",
        "Monitoraggio": "priority-low",
        "Bassa": "priority-low",
    }.get(priority, "priority-mid")

    return badge(priority or "Media", cls)


def compact_role(value: object) -> str:
    roles = split_multi(value)

    if not roles:
        return ""

    cleaned = []

    for role in roles:
        role = clean(role)

        replacements = [
            (" - contractor portfolio / site evidence - data center construction", ""),
            (" - contractor project page - data center construction", ""),
            (" - contractor - ", " · "),
            (" - ", " · "),
        ]

        for old, new in replacements:
            role = role.replace(old, new)

        role = role.replace("Engineering, Procurement and Construction", "EPC")
        role = role.replace("General Contractor / Design & Build", "GC / Design & Build")
        role = role.replace("Civil, Structural and Architectural", "CSA")

        if role and role not in cleaned:
            cleaned.append(role)

    return " | ".join(cleaned[:3])


def contractor_cell(row: dict[str, str]) -> str:
    contractor = clean(row.get("contractor_or_partner")) or "Da identificare"
    conf_html = confidence_badge(row.get("contractor_confidence"))

    if contractor.lower() == "da identificare":
        return '<span class="muted">Da identificare</span>'

    return f'<strong>{esc(contractor)}</strong> {conf_html}'


def row_search_blob(row: dict[str, str]) -> str:
    fields = [
        "project",
        "operator_or_main_subject",
        "mase_proponent",
        "contractor_or_partner",
        "location",
        "region",
        "business_status",
        "business_priority",
        "mase_object_ids",
    ]

    return " ".join(clean(row.get(field)) for field in fields)


def render_kpis(rows: list[dict[str, str]]) -> str:
    by_status = Counter(clean(r.get("business_status")) for r in rows)
    by_priority = Counter(clean(r.get("business_priority")) for r in rows)

    with_contractor = sum(
        1 for r in rows
        if clean(r.get("contractor_or_partner")).lower() not in {"", "da identificare"}
    )

    cards = [
        ("Progetti censiti", len(rows)),
        ("Consolidati", by_status.get("Consolidato", 0)),
        ("Parziali / da verificare", by_status.get("Parziale", 0) + by_status.get("Da verificare", 0)),
        ("Priorità alta", by_priority.get("Alta", 0)),
        ("Con contractor/partner", with_contractor),
        ("MW IT noto", sum(1 for r in rows if clean(r.get("mw_it")))),
        ("MWt noto", sum(1 for r in rows if clean(r.get("thermal_mwt")))),
        ("Superficie nota", sum(1 for r in rows if clean(r.get("site_area_m2")))),
    ]

    return "".join(
        f"""
        <div class="kpi">
          <div class="kpi-label">{esc(label)}</div>
          <div class="kpi-value">{value}</div>
        </div>
        """
        for label, value in cards
    )


def area_lot_display(row: dict[str, str]) -> str:
    project = clean(row.get("project"))

    if project == "Equinix ML9":
        return "22.000 (15.480 sup. costruita)"

    if project == "Equinix ML7-ML8":
        return "14.000 | 10.875 (5.760 sup. costruita)"

    raw = clean(row.get("site_area_m2"))
    parts = split_multi(raw)

    if not parts:
        return "—"

    if len(parts) == 1:
        return format_number(parts[0])

    return '<span class="muted" title="Più valori superficie candidati: verificare nella scheda progetto">Da verificare</span>'


def render_table(rows: list[dict[str, str]]) -> str:
    trs = []

    for r in rows:
        href = project_href(r)
        search_blob = row_search_blob(r)
        status = clean(r.get("business_status"))

        trs.append(f"""
        <tr data-search="{esc(search_blob)}" data-status="{esc(status)}">
          <td class="project-cell">
            <a class="project-link" href="{esc(href)}"><strong>{esc(r.get("project"))}</strong></a>
            <br><span class="muted">ID {value_or_dash(r.get("mase_object_ids"))}</span>
          </td>
          <td>{value_or_dash(r.get("operator_or_main_subject"))}</td>
          <td>{value_or_dash(r.get("mase_proponent"))}</td>
          <td>{contractor_cell(r)}</td>
          <td>{value_or_dash(r.get("location"))}</td>
          <td class="num">{format_mw(r.get("mw_it"))}</td>
          <td class="num">{format_mw(r.get("thermal_mwt"))}</td>
          <td class="num">{area_lot_display(r)}</td>
          <td>{status_badge(r)}</td>
          <td class="sources-cell">{compact_sources(r)}</td>
        </tr>
        """)

    return f"""
    <div class="toolbar">
      <div class="search-box">
        <span class="search-icon">⌕</span>
        <input id="projectSearch" type="search" placeholder="Cerca progetto, operatore, realizzatore, comune..." autocomplete="off">
      </div>

      <select id="qualityFilter" aria-label="Filtro qualità dati">
        <option value="">Tutte le qualità dati</option>
        <option value="Consolidato">OK</option>
        <option value="Da verificare">Verifica</option>
        <option value="Parziale">Parziale</option>
        <option value="Fonti esterne necessarie">Fonti ext.</option>
        <option value="Debole">Debole</option>
      </select>

      <span id="visibleCount" class="counter">{len(rows)} progetti</span>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Progetto</th>
            <th>Operatore</th>
            <th>Proponente MASE</th>
            <th>Realizzatore / partner tecnico</th>
            <th>Comune</th>
            <th>MW IT</th>
            <th>MWt</th>
            <th>Area lotto m²</th>
            <th>Qualità dati</th>
            <th>Fonti</th>
          </tr>
        </thead>
        <tbody>
          {''.join(trs)}
        </tbody>
      </table>
    </div>
    """


def render_home(rows: list[dict[str, str]]) -> str:
    now = datetime.now().isoformat(timespec="seconds")

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Data Center Pipeline Radar</title>
  {base_style()}
</head>
<body>
<header>
  <h1>Data Center Pipeline Radar</h1>
  <p>Vista business multi-fonte dei progetti data center censiti · generata il {esc(now)}</p>
</header>

<main>
  <section class="kpis">
    {render_kpis(rows)}
  </section>

  <section class="panel">
    <h2>Vista immediata progetti</h2>
    {render_table(rows)}
  </section>
</main>

<footer>
  Nota: la tabella fonde fonti MASE, fonti contractor/developer e dati commerciali già censiti. La confidence si riferisce al dato contractor/partner.
</footer>

</body>
</html>
"""


def detail_field(label: str, value: str) -> str:
    return f"""
    <div class="detail-field">
      <dt>{esc(label)}</dt>
      <dd>{value}</dd>
    </div>
    """


def render_project_detail(row: dict[str, str], relative_prefix: str = "../") -> str:
    project = clean(row.get("project"))
    role = compact_role(row.get("contractor_roles"))
    now = datetime.now().isoformat(timespec="seconds")

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(project)} · Data Center Pipeline Radar</title>
  {base_style()}
</head>
<body>
<header>
  <h1>{esc(project)}</h1>
  <p>Dettaglio progetto · generato il {esc(now)}</p>
</header>

<main>
  <nav class="nav">
    <a href="{esc(relative_prefix)}index.html">← Torna alla pipeline</a>
  </nav>

  <section class="panel">
    <div class="detail-head">
      <div>
        <h2>Quadro sintetico</h2>
        <p class="muted">Scheda multi-fonte con separazione tra operatore, proponente MASE, partner tecnico e dati tecnici.</p>
      </div>
      <div class="badges">
        {status_badge(row)}
        {priority_badge(row)}
      </div>
    </div>

    <dl class="detail-grid">
      {detail_field("Operatore / soggetto principale", value_or_dash(row.get("operator_or_main_subject")))}
      {detail_field("Proponente MASE", value_or_dash(row.get("mase_proponent")))}
      {detail_field("Realizzatore / partner tecnico", contractor_cell(row))}
      {detail_field("Ruolo sintetico", esc(role) if role else "—")}
      {detail_field("Comune", value_or_dash(row.get("location")))}
      {detail_field("Regione", value_or_dash(row.get("region")))}
      {detail_field("MASE ID", value_or_dash(row.get("mase_object_ids")))}
      {detail_field("Campus", value_or_dash(row.get("campus_codes")))}
      {detail_field("MW IT", format_mw(row.get("mw_it")))}
      {detail_field("MWt", format_mw(row.get("thermal_mwt")))}
      {detail_field("Area lotto m²", area_lot_display(row))}
      {detail_field("Qualità dati", status_badge(row))}
    </dl>
  </section>

  <section class="panel">
    <h2>Fonti principali</h2>
    <div class="source-box">
      {all_sources(row)}
    </div>
  </section>

  <section class="panel">
    <h2>Azioni e note</h2>
    <div class="next">
      <strong>Prossima azione:</strong> {value_or_dash(row.get("next_action"))}
    </div>

    <div class="note-box">
      <p><strong>Dati mancanti:</strong> {value_or_dash(row.get("missing_fields"))}</p>
      <p><strong>Note tecniche:</strong> {value_or_dash(row.get("technical_notes"))}</p>
    </div>
  </section>
</main>

<footer>
  Fonte base: dc_project_fused_master.csv.
</footer>

</body>
</html>
"""


def base_style() -> str:
    return """
  <style>
    :root {
      --bg:#f5f7fb;
      --panel:#fff;
      --text:#172033;
      --muted:#667085;
      --border:#dfe4ea;
      --shadow:0 10px 24px rgba(15,23,42,.08);
      --green:#166534;
      --blue:#1d4ed8;
      --amber:#92400e;
      --red:#991b1b;
      --slate:#475569;
    }

    * { box-sizing:border-box; }

    body {
      margin:0;
      font-family:Arial, Helvetica, sans-serif;
      background:var(--bg);
      color:var(--text);
      line-height:1.35;
    }

    header {
      background:#111827;
      color:white;
      padding:24px 28px;
    }

    header h1 {
      margin:0 0 6px;
      font-size:28px;
    }

    header p {
      margin:0;
      color:#cbd5e1;
    }

    main {
      max-width:1440px;
      margin:0 auto;
      padding:18px;
    }

    .nav {
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      margin-bottom:16px;
    }

    .nav a, .project-link {
      color:#0f4c81;
      text-decoration:none;
      font-weight:800;
    }

    .nav a {
      background:white;
      border:1px solid var(--border);
      border-radius:999px;
      padding:7px 11px;
      box-shadow:0 4px 10px rgba(15,23,42,.04);
    }

    .project-link:hover, .nav a:hover {
      text-decoration:underline;
    }

    .kpis {
      display:grid;
      grid-template-columns:repeat(4,minmax(0,1fr));
      gap:12px;
      margin-bottom:16px;
    }

    .kpi, .panel {
      background:var(--panel);
      border:1px solid var(--border);
      border-radius:16px;
      box-shadow:var(--shadow);
    }

    .kpi {
      padding:14px;
    }

    .kpi-label {
      color:var(--muted);
      font-size:11px;
      text-transform:uppercase;
      letter-spacing:.05em;
    }

    .kpi-value {
      margin-top:4px;
      font-size:26px;
      font-weight:800;
    }

    .panel {
      padding:14px;
      margin-bottom:16px;
    }

    .panel h2 {
      margin:0 0 12px;
      font-size:20px;
    }

    .table-wrap {
      max-height:72vh;
      overflow-y:auto;
      overflow-x:hidden;
      border:1px solid var(--border);
      border-radius:14px;
    }

    table {
      width:100%;
      table-layout:fixed;
      border-collapse:separate;
      border-spacing:0;
      font-size:12px;
    }

    thead th {
      position:sticky;
      top:0;
      z-index:3;
      background:#f8fafc;
      box-shadow:0 1px 0 var(--border);
    }

    th, td {
      padding:8px 7px;
      border-bottom:1px solid var(--border);
      text-align:left;
      vertical-align:top;
      overflow-wrap:anywhere;
      word-break:normal;
    }

    th {
      color:var(--muted);
      font-size:10px;
      text-transform:uppercase;
      letter-spacing:.04em;
    }

    th:nth-child(1), td:nth-child(1) { width:13%; }
    th:nth-child(2), td:nth-child(2) { width:9%; }
    th:nth-child(3), td:nth-child(3) { width:12%; }
    th:nth-child(4), td:nth-child(4) { width:15%; }
    th:nth-child(5), td:nth-child(5) { width:8%; }
    th:nth-child(6), td:nth-child(6) { width:6%; }
    th:nth-child(7), td:nth-child(7) { width:6%; }
    th:nth-child(8), td:nth-child(8) { width:10%; }
    th:nth-child(9), td:nth-child(9) { width:8%; }
    th:nth-child(10), td:nth-child(10) { width:13%; }

    .num { text-align:right; }

    .project-cell strong {
      font-size:13px;
    }

    .muted {
      color:var(--muted);
      font-size:11px;
      font-weight:400;
    }

    .badge {
      display:inline-flex;
      align-items:center;
      border-radius:999px;
      padding:3px 7px;
      font-size:10px;
      color:white;
      max-width:100%;
      white-space:nowrap;
      font-weight:700;
      margin:1px 2px 1px 0;
    }

    .grade-a { background:var(--green); }
    .grade-b { background:var(--blue); }
    .grade-c { background:var(--amber); }
    .grade-d { background:var(--red); }
    .priority-high { background:var(--red); }
    .priority-mid { background:var(--amber); }
    .priority-low { background:var(--slate); }

    .confidence {
      display:inline-flex;
      align-items:center;
      border-radius:999px;
      padding:3px 7px;
      font-size:10px;
      font-weight:800;
      margin:3px 0 0 5px;
      white-space:nowrap;
    }

    .conf-high {
      background:#dcfce7;
      color:#166534;
      border:1px solid #86efac;
    }

    .conf-mid {
      background:#fef3c7;
      color:#92400e;
      border:1px solid #fcd34d;
    }

    .conf-low {
      background:#fee2e2;
      color:#991b1b;
      border:1px solid #fca5a5;
    }

    .link-pill {
      display:inline-flex;
      border:1px solid var(--border);
      border-radius:999px;
      padding:3px 6px;
      margin:1px 2px 1px 0;
      color:#0f4c81;
      background:#f8fafc;
      text-decoration:none;
      font-weight:700;
      font-size:10px;
      white-space:nowrap;
    }

    .sources-cell {
      line-height:1.35;
    }

    .detail-head {
      display:flex;
      justify-content:space-between;
      align-items:flex-start;
      gap:16px;
      margin-bottom:12px;
    }

    .badges {
      min-width:170px;
      text-align:right;
    }

    .detail-grid {
      display:grid;
      grid-template-columns:repeat(3,minmax(0,1fr));
      gap:12px;
      margin:0;
    }

    .detail-field {
      background:#f8fafc;
      border:1px solid var(--border);
      border-radius:14px;
      padding:12px;
    }

    dt {
      color:var(--muted);
      font-size:10px;
      text-transform:uppercase;
      letter-spacing:.05em;
    }

    dd {
      margin:2px 0 0;
      font-weight:700;
      word-break:break-word;
    }

    .source-box, .next, .note-box {
      margin-top:10px;
      padding:12px;
      border-radius:14px;
      font-size:13px;
    }

    .source-box {
      border:1px solid #bfdbfe;
      background:#eff6ff;
    }

    .source-box div + div {
      margin-top:8px;
    }

    .next {
      border:1px solid #fed7aa;
      background:#fff7ed;
    }

    .note-box {
      border:1px solid var(--border);
      background:#f8fafc;
    }

    footer {
      max-width:1440px;
      margin:0 auto;
      padding:0 18px 30px;
      color:var(--muted);
      font-size:12px;
    }


    /* --- Tech skin ------------------------------------------------ */

    body {
      background:
        radial-gradient(circle at 10% 0%, rgba(14,165,233,.18), transparent 28%),
        radial-gradient(circle at 92% 12%, rgba(99,102,241,.16), transparent 30%),
        linear-gradient(180deg, #eef4fb 0%, #f8fafc 52%, #eef2f7 100%);
    }

    header {
      position:relative;
      overflow:hidden;
      background:
        radial-gradient(circle at 12% 20%, rgba(56,189,248,.35), transparent 26%),
        radial-gradient(circle at 86% 5%, rgba(129,140,248,.28), transparent 28%),
        linear-gradient(135deg, #08111f 0%, #10243f 44%, #0f4c81 100%);
      border-bottom:1px solid rgba(255,255,255,.16);
      box-shadow:0 18px 46px rgba(15,23,42,.22);
    }

    header::before {
      content:"";
      position:absolute;
      inset:-80px -120px auto auto;
      width:360px;
      height:360px;
      border-radius:999px;
      background:radial-gradient(circle, rgba(34,211,238,.26), transparent 66%);
      filter:blur(4px);
      pointer-events:none;
    }

    header::after {
      content:"";
      position:absolute;
      inset:0;
      background:
        linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px),
        linear-gradient(180deg, rgba(255,255,255,.04) 1px, transparent 1px);
      background-size:44px 44px;
      mask-image:linear-gradient(90deg, rgba(0,0,0,.35), transparent 80%);
      pointer-events:none;
    }

    header h1,
    header p {
      position:relative;
      z-index:1;
    }

    header h1 {
      letter-spacing:-.03em;
    }

    header p {
      max-width:840px;
    }

    .kpi {
      position:relative;
      overflow:hidden;
      background:
        linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.78));
      backdrop-filter: blur(12px);
      transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }

    .kpi::before {
      content:"";
      position:absolute;
      left:0;
      top:0;
      right:0;
      height:3px;
      background:linear-gradient(90deg, #0ea5e9, #6366f1, #22c55e);
    }

    .kpi:hover {
      transform:translateY(-2px);
      box-shadow:0 16px 32px rgba(15,23,42,.12);
      border-color:#c7d2fe;
    }

    .kpi-value {
      background:linear-gradient(135deg, #0f172a, #0f4c81);
      -webkit-background-clip:text;
      background-clip:text;
      color:transparent;
    }

    .panel {
      background:rgba(255,255,255,.86);
      backdrop-filter: blur(14px);
      border-color:rgba(148,163,184,.32);
    }

    .panel h2 {
      letter-spacing:-.02em;
    }

    .toolbar {
      display:flex;
      align-items:center;
      gap:10px;
      margin:0 0 12px;
      flex-wrap:wrap;
    }

    .search-box {
      flex:1 1 360px;
      display:flex;
      align-items:center;
      gap:8px;
      height:40px;
      padding:0 12px;
      border:1px solid rgba(148,163,184,.42);
      border-radius:999px;
      background:rgba(248,250,252,.94);
      box-shadow:inset 0 1px 0 rgba(255,255,255,.7);
    }

    .search-icon {
      color:#0f4c81;
      font-weight:900;
      font-size:18px;
      line-height:1;
    }

    .search-box input {
      width:100%;
      border:0;
      outline:0;
      background:transparent;
      color:var(--text);
      font-size:13px;
      font-weight:700;
    }

    .search-box input::placeholder {
      color:#94a3b8;
      font-weight:600;
    }

    .toolbar select {
      height:40px;
      border:1px solid rgba(148,163,184,.42);
      border-radius:999px;
      background:#fff;
      color:#172033;
      padding:0 12px;
      font-weight:800;
      font-size:12px;
      outline:0;
    }

    .counter {
      height:40px;
      display:inline-flex;
      align-items:center;
      padding:0 12px;
      border-radius:999px;
      color:#0f4c81;
      background:#eff6ff;
      border:1px solid #bfdbfe;
      font-weight:900;
      font-size:12px;
      white-space:nowrap;
    }

    .table-wrap {
      box-shadow:inset 0 1px 0 rgba(255,255,255,.7);
      background:white;
    }

    thead th {
      background:linear-gradient(180deg, #f8fafc 0%, #eef4fb 100%);
      color:#536078;
    }

    tbody tr {
      transition:background .14s ease, transform .14s ease, box-shadow .14s ease;
    }

    tbody tr:hover {
      background:#f8fbff;
    }

    tbody tr:hover td:first-child {
      box-shadow:inset 3px 0 0 #0ea5e9;
    }

    .project-link strong {
      color:#0f172a;
      transition:color .14s ease;
    }

    .project-link:hover strong {
      color:#0f4c81;
    }

    .badge,
    .confidence,
    .link-pill {
      box-shadow:0 1px 0 rgba(255,255,255,.42) inset;
    }

    .grade-a {
      background:linear-gradient(135deg, #15803d, #16a34a);
    }

    .grade-b {
      background:linear-gradient(135deg, #1d4ed8, #2563eb);
    }

    .grade-c {
      background:linear-gradient(135deg, #9a3412, #ea580c);
    }

    .grade-d {
      background:linear-gradient(135deg, #991b1b, #dc2626);
    }

    .link-pill {
      background:linear-gradient(180deg, #ffffff, #f1f5f9);
      border-color:#d8e2ee;
    }

    .link-pill:hover {
      background:#eff6ff;
      border-color:#93c5fd;
      text-decoration:none;
    }

    .detail-field {
      transition:transform .16s ease, box-shadow .16s ease;
    }

    .detail-field:hover {
      transform:translateY(-1px);
      box-shadow:0 10px 20px rgba(15,23,42,.07);
    }

    @media (max-width:1000px) {
      .kpis { grid-template-columns:repeat(2,minmax(0,1fr)); }
      .table-wrap { overflow-x:auto; }
      table { min-width:1050px; }
      .detail-grid { grid-template-columns:1fr; }
      .detail-head { flex-direction:column; }
      .badges { text-align:left; }
    }

    @media (max-width:560px) {
      main { padding:12px; }
      header { padding:20px 16px; }
      .kpis { grid-template-columns:1fr; }
    }
  </style>
"""



def filter_script() -> str:
    return """<script>
(function () {
  const search = document.getElementById("projectSearch");
  const quality = document.getElementById("qualityFilter");
  const count = document.getElementById("visibleCount");
  const rows = Array.from(document.querySelectorAll("tbody tr[data-search]"));

  if (!search || !quality || !rows.length) return;

  function applyFilters() {
    const q = search.value.trim().toLowerCase();
    const selectedQuality = quality.value;
    let visible = 0;

    for (const row of rows) {
      const haystack = (row.dataset.search || "").toLowerCase();
      const status = row.dataset.status || "";

      const matchesSearch = !q || haystack.includes(q);
      const matchesQuality = !selectedQuality || status === selectedQuality;
      const show = matchesSearch && matchesQuality;

      row.style.display = show ? "" : "none";
      if (show) visible += 1;
    }

    if (count) {
      count.textContent = visible === 1 ? "1 progetto" : visible + " progetti";
    }
  }

  search.addEventListener("input", applyFilters);
  quality.addEventListener("change", applyFilters);
})();
</script>"""

def write_project_pages(rows: list[dict[str, str]]) -> None:
    DOCS_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    for row in rows:
        filename = f"{slugify(row.get('project'))}.html"
        html_doc = render_project_detail(row, relative_prefix="../")

        (DOCS_PROJECTS_DIR / filename).write_text(html_doc, encoding="utf-8")
        (REPORTS_PROJECTS_DIR / filename).write_text(html_doc, encoding="utf-8")


def main() -> None:
    rows = read_csv(INPUT)

    if not rows:
        raise FileNotFoundError(f"No rows found in {INPUT}")

    html_doc = render_home(rows)

    DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_INDEX.parent.mkdir(parents=True, exist_ok=True)

    DOCS_INDEX.write_text(html_doc, encoding="utf-8")
    DOCS_LEGACY.write_text(html_doc, encoding="utf-8")
    REPORTS_INDEX.write_text(html_doc, encoding="utf-8")
    REPORTS_LEGACY.write_text(html_doc, encoding="utf-8")

    write_project_pages(rows)

    JSON_OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] Written {DOCS_INDEX}")
    print(f"[OK] Written {DOCS_LEGACY}")
    print(f"[OK] Written {REPORTS_INDEX}")
    print(f"[OK] Written {REPORTS_LEGACY}")
    print(f"[OK] Written project pages in {DOCS_PROJECTS_DIR}")
    print(f"[OK] Written {JSON_OUT}")


if __name__ == "__main__":
    main()
