from __future__ import annotations

import csv
import html
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus


INPUT = Path("data/output/external_sources/datacentermap_promotion_draft.csv")
OUT_DIR = Path("docs/projects")


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

FACT_PREFIX_LABELS = {
    "operator_site": "Fonte operatore",
    "regional_via_vas": "Fonte regionale",
    "municipality_suap_albo": "Comune / SUAP",
    "mase": "MASE",
    "contractor_gc": "GC / contractor",
}

CSS = r"""
:root {
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
}
* { box-sizing:border-box; }
body {
  margin:0;
  font-family:Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}
header {
  background:linear-gradient(135deg,var(--dark),var(--blue));
  color:white;
  padding:26px 30px;
}
header h1 {
  margin:0;
  font-size:30px;
}
header p {
  margin:8px 0 0;
  color:#dbeafe;
}
main {
  max-width:1500px;
  margin:0 auto;
  padding:20px;
}
.nav {
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  margin-bottom:16px;
}
.nav a {
  color:var(--blue);
  font-weight:800;
  text-decoration:none;
}
.panel {
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:18px;
  margin-bottom:16px;
}
.section-title {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin-bottom:14px;
}
h2 {
  margin:0;
  font-size:20px;
}
.subtle {
  color:var(--muted);
  font-size:13px;
}
.grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:12px;
}
.field {
  position:relative;
  overflow:hidden;
  min-height:112px;
  background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%);
  border:1px solid var(--line);
  border-radius:16px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:18px 16px 16px;
  display:flex;
  flex-direction:column;
  justify-content:space-between;
}
.field::before {
  content:"";
  position:absolute;
  top:0;
  left:0;
  right:0;
  height:4px;
  background:linear-gradient(90deg,#0ea5e9,#6366f1,#22c55e);
}
.field:hover {
  background:#ffffff;
}
.label {
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.055em;
  margin-bottom:8px;
  font-weight:700;
}
.value {
  margin:0;
  font-size:20px;
  line-height:1.22;
  font-weight:900;
  color:#0f172a;
  overflow-wrap:anywhere;
}
.value .badge {
  font-size:12px;
}
.badge {
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  font-weight:800;
  font-size:12px;
}
.badge.good {
  background:var(--good-bg);
  color:var(--good);
}
.badge.warn {
  background:var(--warn-bg);
  color:var(--warn);
}
.badge.neutral {
  background:var(--neutral-bg);
  color:var(--neutral);
}
.actions {
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-top:12px;
}
.btn, .source-pill {
  display:inline-block;
  padding:7px 11px;
  border-radius:999px;
  background:var(--neutral-bg);
  color:var(--neutral);
  text-decoration:none;
  font-weight:800;
  font-size:13px;
}
.btn.maps {
  background:var(--good-bg);
  color:var(--good);
}
.location-card {
  position:relative;
  overflow:hidden;
  background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%);
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:20px 18px 18px;
}
.location-card::before {
  content:"";
  position:absolute;
  top:0;
  left:0;
  right:0;
  height:4px;
  background:linear-gradient(90deg,#0ea5e9,#6366f1,#22c55e);
}
.location-card h2 {
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.055em;
  font-weight:800;
  margin:0;
}
.location-address {
  color:#0f172a;
  font-size:15px;
  font-weight:800;
}

.map-wrap {
  border:1px solid var(--line);
  border-radius:16px;
  overflow:hidden;
  background:#e5e7eb;
  margin-top:14px;
}
.map-wrap iframe {
  display:block;
  width:100%;
  height:360px;
  border:0;
}
.two-col {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
}
.content-card {
  position:relative;
  overflow:hidden;
  background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%);
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:20px 18px 18px;
}
.content-card::before {
  content:"";
  position:absolute;
  top:0;
  left:0;
  right:0;
  height:4px;
  background:linear-gradient(90deg,#0ea5e9,#6366f1,#22c55e);
}
.content-card h2 {
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.055em;
  font-weight:800;
  margin:0 0 14px;
}
.content-card p,
.content-card li {
  font-size:15px;
  line-height:1.5;
}
.content-card strong {
  color:#0f172a;
}
.content-card .source-pill {
  margin:0 6px 8px 0;
}

ul.clean {
  margin:0;
  padding-left:20px;
}
ul.clean li {
  margin:0 0 8px;
  line-height:1.45;
}
.evidence-list {
  margin:0;
  padding-left:20px;
}
.evidence-list li {
  margin:0 0 10px;
  line-height:1.45;
}
.muted {
  color:var(--muted);
}
.warning-box {
  background:#fff7ed;
  border:1px solid #fed7aa;
  color:#92400e;
  border-radius:14px;
  padding:12px 14px;
  font-weight:700;
}
@media (max-width:1000px) {
  .grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .two-col { grid-template-columns:1fr; }
}
@media (max-width:640px) {
  .grid { grid-template-columns:1fr; }
  header h1 { font-size:24px; }
}
"""


def clean(value: object) -> str:
    return str(value or "").strip()


def esc(value: object) -> str:
    return html.escape(clean(value), quote=True)


def norm_text(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("à", "a").replace("è", "e").replace("é", "e")
    value = value.replace("ì", "i").replace("ò", "o").replace("ù", "u")
    return value


def slugify(value: str) -> str:
    value = norm_text(value)
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def read_rows() -> list[dict[str, str]]:
    if not INPUT.exists():
        raise SystemExit(f"File non trovato: {INPUT}")

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def quality(row: dict[str, str]) -> tuple[str, str, str]:
    readiness = clean(row.get("readiness"))

    if readiness in {"ready_with_gc", "ready_missing_gc"}:
        return ("OK", "good", "Dati principali coerenti e utilizzabili per review master.")

    if readiness in {"partial_public_confirmation", "operator_confirmed_only"}:
        return ("Parziale", "warn", "Progetto valido, ma con informazioni ancora da completare.")

    return ("Fonti ext.", "neutral", "Record utile come fonte esterna o enrichment, da non trattare automaticamente come nuovo master.")


def maps_query(row: dict[str, str]) -> str:
    address = clean(row.get("address"))
    if address:
        return address

    name = clean(row.get("proposed_project_name"))
    city = clean(row.get("city"))
    return " ".join(part for part in [name, city, "data center", "Italia"] if part)


def maps_url(row: dict[str, str]) -> str:
    url = clean(row.get("google_maps_url"))
    if url:
        return url

    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(maps_query(row))


def maps_embed_url(row: dict[str, str]) -> str:
    return "https://www.google.com/maps?q=" + quote_plus(maps_query(row)) + "&output=embed"


def link_button(label: str, url: str, cls: str = "") -> str:
    if not clean(url):
        return ""

    return f'<a class="btn {esc(cls)}" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def dcm_url(row: dict[str, str]) -> str:
    return clean(row.get("dcm_source_url"))


def thermal_power_value(row: dict[str, str]) -> str:
    for key in [
        "thermal_power_mwt",
        "primary_thermal_power_mwt",
        "mwt",
        "thermal_power",
    ]:
        value = clean(row.get(key))
        if value:
            return value

    return ""


def field(label: str, value: object) -> str:
    v = esc(value) if clean(value) else "—"

    return f"""
      <div class="field">
        <div class="label">{esc(label)}</div>
        <p class="value">{v}</p>
      </div>
    """


def quality_field(row: dict[str, str]) -> str:
    label, cls, title = quality(row)

    return f"""
      <div class="field">
        <div class="label">Qualità dati</div>
        <p class="value"><span class="badge {esc(cls)}" title="{esc(title)}">{esc(label)}</span></p>
      </div>
    """


def source_links_html(row: dict[str, str]) -> str:
    raw = clean(row.get("source_links"))
    items: list[str] = []

    if raw:
        pos = 0

        for match in re.finditer(r"<([^<>]+)>", raw):
            label = raw[pos:match.start()].strip().strip("|").strip()
            url = match.group(1).strip()

            if label and url:
                items.append(
                    f'<a class="source-pill" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'
                )

            pos = match.end()

        tail = raw[pos:].strip().strip("|").strip()
        if tail:
            items.append(f'<span class="source-pill">{esc(tail)}</span>')

    dcm = dcm_url(row)
    if dcm and dcm not in " ".join(items):
        items.append(
            f'<a class="source-pill" href="{esc(dcm)}" target="_blank" rel="noopener">DataCenterMap</a>'
        )

    if not items:
        return '<span class="muted">Nessuna fonte linkabile disponibile.</span>'

    return " ".join(items)


def sentence(value: str) -> str:
    value = clean(value)
    value = value.rstrip(" .")
    return value + "." if value else ""


def project_summary_items(row: dict[str, str]) -> list[str]:
    items: list[str] = []

    name = clean(row.get("proposed_project_name"))
    operator = clean(row.get("operator_or_main_subject"))
    city = clean(row.get("city"))
    status = clean(row.get("dcm_status"))
    mw = clean(row.get("it_power_mw"))
    area = clean(row.get("site_area_m2"))
    proponent = clean(row.get("authorization_proponent"))
    contractor = clean(row.get("contractor_or_partner"))

    if operator:
        items.append(f"Operatore individuato: {sentence(operator)}")
    if city:
        items.append(f"Ubicazione commerciale censita: {sentence(city)}")
    if status:
        items.append(f"Stato indicato dalla fonte DataCenterMap: {sentence(status)}")
    if mw:
        items.append(f"Potenza IT censita: {sentence(mw)}")

    thermal = thermal_power_value(row)
    if thermal:
        items.append(f"Potenza termica censita: {sentence(thermal)}")

    if area:
        items.append(f"Superficie censita: {sentence(area)}")
    if proponent and proponent.lower() not in {"da verificare", "da identificare"}:
        items.append(f"Proponente/soggetto autorizzativo individuato: {sentence(proponent)}")
    if contractor and contractor.lower() not in {"da verificare", "da identificare"}:
        items.append(f"GC/contractor o partner individuato: {sentence(contractor)}")
    elif contractor:
        items.append("GC/contractor ancora da identificare.")

    readiness = clean(row.get("readiness"))

    if readiness == "existing_project_child_or_enrichment":
        items.append("Il record va trattato come espansione, sotto-facility o arricchimento di un progetto già censito, non come nuovo master autonomo.")
    elif readiness == "existing_operational_reference":
        items.append("Il record sembra riferirsi a un asset esistente/reference, non a una pipeline futura da promuovere come nuovo progetto.")
    elif readiness == "operator_confirmed_only":
        items.append("Il progetto è confermato dall’operatore, ma mancano ancora riscontri pubblici/locali sufficienti.")
    elif readiness == "partial_public_confirmation":
        items.append("Il progetto ha conferme pubbliche parziali, ma il quadro informativo non è ancora completo.")
    elif readiness in {"ready_with_gc", "ready_missing_gc"}:
        items.append("Il record è abbastanza solido per essere valutato insieme ai progetti principali.")

    if not items:
        items.append(f"Record censito come {name} da fonte DataCenterMap.")

    return items


def operational_notes(row: dict[str, str]) -> list[str]:
    notes: list[str] = []
    readiness = clean(row.get("readiness"))
    contractor = clean(row.get("contractor_or_partner"))
    dcm_status = clean(row.get("dcm_status"))

    if readiness in {"ready_with_gc", "ready_missing_gc"}:
        notes.append("Da trattare come candidato commerciale ad alta priorità di review.")
    elif readiness == "partial_public_confirmation":
        notes.append("Da mantenere in evidenza, ma con verifica ulteriore su fonti locali, iter autorizzativo o GC.")
    elif readiness == "operator_confirmed_only":
        notes.append("Da monitorare: utile per prospecting, ma non ancora abbastanza robusto per assunzioni operative forti.")
    elif readiness == "existing_project_child_or_enrichment":
        notes.append("Non duplicare nel master: collegare al progetto/campus principale come espansione o dettaglio tecnico.")
    elif readiness == "existing_operational_reference":
        notes.append("Non considerare come nuova pipeline: utile come riferimento di mercato o asset esistente.")

    if contractor and contractor.lower() in {"da identificare", "da verificare"}:
        notes.append("Priorità informativa: identificare GC, EPC, impresa esecutrice o partner tecnico.")

    if dcm_status:
        notes.append(f"Lo stato DataCenterMap va letto come indicazione commerciale grezza: {dcm_status}.")

    return notes


def evidence_items(value: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []

    for part in clean(value).split("||"):
        part = clean(part)
        if not part:
            continue

        label = "Evidenza"
        body = part

        if ":" in part:
            prefix, rest = part.split(":", 1)
            prefix_key = clean(prefix)
            body = clean(rest)
            label = FACT_PREFIX_LABELS.get(prefix_key, prefix_key)

        body_l = body.lower()

        if body_l.startswith("no direct ") or body_l.startswith("no reliable ") or body_l.startswith("no mase "):
            continue

        if body:
            items.append((label, body))

    return items


def render_list(items: list[str]) -> str:
    if not items:
        return "<p class=\"muted\">—</p>"

    return "<ul class=\"clean\">" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"


def render_evidence(row: dict[str, str]) -> str:
    items = evidence_items(clean(row.get("summary_facts")))

    if not items:
        return '<p class="muted">Nessuna evidenza sintetica aggiuntiva oltre alle fonti linkate.</p>'

    lis = []
    for label, body in items:
        lis.append(f"<li><strong>{esc(label)}:</strong> {esc(body)}</li>")

    return "<ul class=\"evidence-list\">" + "".join(lis) + "</ul>"


def render(row: dict[str, str]) -> str:
    name = clean(row.get("proposed_project_name"))
    generated_at = datetime.now().isoformat(timespec="seconds")
    q_label, q_cls, q_title = quality(row)

    maps = link_button("Apri in Google Maps", maps_url(row), "maps")
    dcm = link_button("DataCenterMap", dcm_url(row))

    subtitle_parts = [
        clean(row.get("operator_or_main_subject")),
        clean(row.get("city")),
        q_label,
    ]
    subtitle = " · ".join(x for x in subtitle_parts if x)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(name)} - Data Center Radar</title>
<style>
{CSS}
</style>
</head>
<body>
<header>
  <h1>{esc(name)}</h1>
  <p>{esc(subtitle)} · scheda generata il {esc(generated_at)}</p>
</header>
<main>
  <div class="nav">
    <a href="../index.html">← Torna alla dashboard principale</a>
    <span class="subtle">Fonte discovery: DataCenterMap + review interna</span>
  </div>

  <section class="panel">
    <div class="section-title">
      <h2>Dati principali</h2>
    </div>
    <div class="grid">
      {field("Operatore", row.get("operator_or_main_subject"))}
      {field("Proponente", row.get("authorization_proponent"))}
      {field("GC / contractor", row.get("contractor_or_partner"))}
      {field("Stato fonte", row.get("dcm_status"))}
      {field("MWt", thermal_power_value(row))}
      {field("MW IT", row.get("it_power_mw"))}
      {field("Superficie", row.get("site_area_m2"))}
      {quality_field(row)}
    </div>
  </section>

  <section class="panel location-card">
    <div class="section-title">
      <h2>Ubicazione</h2>
      <span class="location-address">{esc(row.get("address")) or "Indirizzo non disponibile"}</span>
    </div>
    <div class="actions">
      {maps}
      {dcm}
    </div>
    <div class="map-wrap">
      <iframe src="{esc(maps_embed_url(row))}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </div>
  </section>

  <section class="two-col">
    <div class="panel content-card">
      <h2>Sintesi progetto</h2>
      {render_list(project_summary_items(row))}
    </div>

    <div class="panel content-card">
      <h2>Note operative</h2>
      {render_list(operational_notes(row))}
    </div>
  </section>

  <section class="panel content-card">
    <h2>Evidenze disponibili</h2>
    {render_evidence(row)}
  </section>

  <section class="panel content-card">
    <h2>Fonti</h2>
    <p>{source_links_html(row)}</p>
  </section>
</main>
</body>
</html>
"""


def main() -> None:
    rows = read_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for row in rows:
        name = clean(row.get("proposed_project_name"))
        out = OUT_DIR / f"{slugify(name)}.html"

        html_out = render(row)
        html_out = "\n".join(line.rstrip() for line in html_out.splitlines()) + "\n"

        out.write_text(html_out, encoding="utf-8")
        print(f"[OK] Written {out}")

    print(f"[OK] Generated {len(rows)} DataCenterMap project pages")


if __name__ == "__main__":
    main()
