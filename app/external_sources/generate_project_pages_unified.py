from __future__ import annotations

import argparse
import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus


MASTER_JSON = Path("docs/dc_project_fused_master.json")
DCM_CSV = Path("data/output/external_sources/datacentermap_promotion_draft.csv")

PREVIEW_DIR = Path("docs/projects_unified_preview")
APPLY_DIR = Path("docs/projects")


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
header h1 { margin:0; font-size:30px; }
header p { margin:8px 0 0; color:#dbeafe; }
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
h2 { margin:0; font-size:20px; }
.subtle { color:var(--muted); font-size:13px; }
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
.value .badge { font-size:12px; }
.badge {
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  font-weight:800;
  font-size:12px;
}
.badge.good { background:var(--good-bg); color:var(--good); }
.badge.warn { background:var(--warn-bg); color:var(--warn); }
.badge.neutral { background:var(--neutral-bg); color:var(--neutral); }
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
.location-card,
.content-card {
  position:relative;
  overflow:hidden;
  background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%);
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:20px 18px 18px;
}
.location-card::before,
.content-card::before {
  content:"";
  position:absolute;
  top:0;
  left:0;
  right:0;
  height:4px;
  background:linear-gradient(90deg,#0ea5e9,#6366f1,#22c55e);
}
.location-card h2,
.content-card h2 {
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.055em;
  font-weight:800;
  margin:0 0 14px;
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
ul.clean,
.evidence-list {
  margin:0;
  padding-left:20px;
}
ul.clean li,
.evidence-list li,
.content-card p {
  font-size:15px;
  line-height:1.5;
  margin-bottom:8px;
}
.content-card strong { color:#0f172a; }
.content-card .source-pill { margin:0 6px 8px 0; }
.muted { color:var(--muted); }
@media (max-width:1000px) {
  .grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .two-col { grid-template-columns:1fr; }
}
@media (max-width:640px) {
  .grid { grid-template-columns:1fr; }
  header h1 { font-size:24px; }
}
"""


FACT_LABELS = {
    "operator_site": "Fonte operatore",
    "regional_via_vas": "Fonte regionale",
    "municipality_suap_albo": "Comune / SUAP",
    "mase": "MASE",
    "contractor_gc": "GC / contractor",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def esc(value: object) -> str:
    return html.escape(clean(value), quote=True)


def slugify(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = value.replace("à", "a").replace("è", "e").replace("é", "e")
    value = value.replace("ì", "i").replace("ò", "o").replace("ù", "u")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def split_pipe(value: str) -> list[str]:
    value = clean(value)
    if not value:
        return []
    parts = re.split(r"\s*\|\s*|\s*\|\|\s*", value)
    return [p.strip() for p in parts if p.strip()]


def source_pills(labels: str, urls: str, fallback_label: str = "") -> list[str]:
    label_parts = split_pipe(labels)
    url_parts = split_pipe(urls)
    pills = []

    # Regola: in Fonti entrano solo URL reali. Niente chip di categoria senza link.
    if not url_parts:
        return pills

    for i, url in enumerate(url_parts):
        url = clean(url)
        if not url:
            continue

        label = label_parts[i] if i < len(label_parts) else fallback_label or "Fonte"

        # Evita etichette tecniche o generiche.
        if label.lower() in {
            "manual confirmed contractor lead",
            "contractor / partner",
            "mw it",
            "mwt",
            "superficie",
            "fonte",
            "source",
        }:
            label = fallback_label or url

        pills.append(
            f'<a class="source-pill" href="{esc(url)}" target="_blank" rel="noopener">{esc(label or url)}</a>'
        )

    return pills


def strip_unit(value: str, kind: str) -> str:
    value = clean(value)

    if not value:
        return ""

    if kind == "mw_it":
        value = re.sub(r"\s*MW\s*$", "", value, flags=re.I)

    elif kind == "mwt":
        value = re.sub(r"\s*MWt\s*$", "", value, flags=re.I)
        value = re.sub(r"\s*MW\s+termici\s*$", "", value, flags=re.I)

    elif kind == "area":
        value = re.sub(r"\s*m²\s*$", "", value, flags=re.I)
        value = re.sub(r"\s*mq\s*$", "", value, flags=re.I)
        value = re.sub(r"\s*sqm\s*$", "", value, flags=re.I)

    return value.strip()


def value_with_unit(value: str, unit: str) -> str:
    value = clean(value)

    if not value:
        return ""

    if unit.lower() in value.lower():
        return sentence(value)

    return sentence(f"{value} {unit}")


def area_with_unit(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    if "m²" in value.lower() or "mq" in value.lower() or "sqm" in value.lower():
        return sentence(value)

    # Caso tipico: 13.000 (3.500 sup. costruita)
    m = re.match(r"^([0-9.,]+)\s*\(([0-9.,]+)\s*(.*?)\)$", value)

    if m:
        total, built, label = m.groups()
        return sentence(f"{total} m² ({built} m² {label})")

    return sentence(f"{value} m²")


def field_name_it(value: str) -> str:
    mapping = {
        "thermal_mwt": "MWt",
        "thermal_power_mwt": "MWt",
        "site_area_m2": "superficie",
        "mw_it": "MW IT",
        "contractor_or_partner": "GC/contractor",
        "mase_proponent": "proponente",
    }

    parts = split_pipe(value)
    out = [mapping.get(p, p) for p in parts]

    return " | ".join(out)


def dedup_pipe(value: str) -> str:
    seen = set()
    out = []

    for part in split_pipe(value):
        if part.lower() in seen:
            continue
        seen.add(part.lower())
        out.append(part)

    return " | ".join(out)


def roles_to_italian(value: str) -> str:
    value = clean(value)

    if not value:
        return ""

    replacements = {
        "Engineering / design": "ingegneria / progettazione",
        "engineering / energy": "ingegneria / energia",
        "Energy / district cooling": "energia / district cooling",
        "energy / cooling": "energia / raffrescamento",
        " - ": ": ",
        " || ": "; ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def layer_name_it(value: str) -> str:
    mapping = {
        "operator_site": "fonte operatore",
        "regional_via_vas": "fonte regionale / VIA-VAS",
        "municipality_suap_albo": "Comune / SUAP / albo pretorio",
        "mase": "MASE",
        "contractor_gc": "GC / contractor",
    }

    return mapping.get(clean(value), clean(value))

def quality_from_status(status: str, readiness: str = "") -> tuple[str, str, str]:
    blob = f"{status} {readiness}".lower()

    if "consolidato" in blob or "ready_with_gc" in blob or "ready_missing_gc" in blob:
        return ("OK", "good", "Dati principali coerenti e utilizzabili.")

    if "parziale" in blob or "operator_confirmed_only" in blob or "partial_public_confirmation" in blob:
        return ("Parziale", "warn", "Progetto valido, ma con informazioni ancora da completare.")

    if "fonti" in blob or "tracked" in blob or "child" in blob or "existing" in blob or "pending" in blob:
        return ("Fonti ext.", "neutral", "Servono fonti aggiuntive o verifica manuale.")

    return ("—", "neutral", "Qualità dati non classificata.")


def sentence(value: str) -> str:
    value = clean(value).rstrip(" .")
    return value + "." if value else ""


def field_card(label: str, value: str) -> str:
    value = clean(value) or "—"
    return f"""
      <div class="field">
        <div class="label">{esc(label)}</div>
        <p class="value">{esc(value)}</p>
      </div>
    """


def quality_card(label: str, cls: str, title: str) -> str:
    return f"""
      <div class="field">
        <div class="label">Qualità dati</div>
        <p class="value"><span class="badge {esc(cls)}" title="{esc(title)}">{esc(label)}</span></p>
      </div>
    """


def list_html(items: list[str]) -> str:
    if not items:
        return '<p class="muted">—</p>'
    return '<ul class="clean">' + "".join(f"<li>{esc(x)}</li>" for x in items if clean(x)) + "</ul>"


def evidence_html(items: list[tuple[str, str]]) -> str:
    if not items:
        return '<p class="muted">Nessuna evidenza sintetica aggiuntiva disponibile.</p>'

    lis = []
    for label, body in items:
        lis.append(f"<li><strong>{esc(label)}:</strong> {esc(body)}</li>")
    return '<ul class="evidence-list">' + "".join(lis) + "</ul>"


def maps_url(query: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def maps_embed(query: str) -> str:
    return "https://www.google.com/maps?q=" + quote_plus(query) + "&output=embed"


def translate_status(value: str) -> str:
    value = clean(value)

    mapping = {
        "Planned": "Pianificato",
        "Under Construction": "In costruzione",
        "Land Banked": "Area acquisita",
        "Operational": "Operativo",
        "Existing": "Esistente",
    }

    return mapping.get(value, value)


def translate_note(value: str) -> str:
    value = clean(value)

    mapping = {
        "MASE PDF extraction": "estrarre e verificare i PDF MASE",
    }

    return mapping.get(value, value)



def master_record_to_page(r: dict[str, str]) -> dict[str, object]:
    project = clean(r.get("project"))
    status = clean(r.get("business_status"))
    q_label, q_cls, q_title = quality_from_status(status)

    location = clean(r.get("location")) or "Da identificare"
    if location == "Da identificare":
        map_query = f"{project} data center Italia"
    else:
        map_query = f"{project} {location} data center Italia"

    mwt_raw = clean(r.get("thermal_power_mwt") or r.get("thermal_mwt"))
    mw_it_raw = clean(r.get("mw_it"))
    area_raw = clean(r.get("site_area_m2"))

    summary = [
        f"Operatore individuato: {sentence(r.get('operator_or_main_subject'))}" if clean(r.get("operator_or_main_subject")) else "",
        f"Proponente/soggetto autorizzativo: {sentence(r.get('mase_proponent'))}" if clean(r.get("mase_proponent")) else "",
        f"GC/contractor o partner: {sentence(r.get('contractor_or_partner'))}" if clean(r.get("contractor_or_partner")) else "",
        f"Localizzazione censita: {sentence(location)}" if location else "",
        f"Stato commerciale: {sentence(status)}" if status else "",
        f"Priorità commerciale: {sentence(r.get('business_priority'))}" if clean(r.get("business_priority")) else "",
        f"Potenza termica censita: {value_with_unit(mwt_raw, 'MWt')}" if mwt_raw else "",
        f"Potenza IT censita: {value_with_unit(mw_it_raw, 'MW')}" if mw_it_raw else "",
        f"Superficie censita: {area_with_unit(area_raw)}" if area_raw else "",
    ]

    notes = []
    if clean(r.get("next_action")):
        notes.append(f"Prossima azione: {sentence(translate_note(r.get('next_action')))}")
    if clean(r.get("missing_fields")):
        notes.append(f"Campi mancanti: {sentence(r.get('missing_fields'))}")
    if clean(r.get("contractor_confidence")):
        notes.append(f"Affidabilità contractor/partner: {clean(r.get('contractor_confidence'))}%.")
    if not notes:
        notes.append("Scheda da usare come supporto commerciale e come base per ulteriori verifiche.")

    evidence = []
    if clean(r.get("mase_object_ids")):
        evidence.append(("MASE", f"Oggetto/i MASE: {clean(r.get('mase_object_ids'))}."))
    if clean(r.get("contractor_roles")):
        evidence.append(("Ruoli contractor/partner", roles_to_italian(r.get("contractor_roles"))))
    if clean(r.get("technical_notes")):
        evidence.append(("Note tecniche", clean(r.get("technical_notes"))))
    if clean(r.get("external_promoted_fields")):
        evidence.append(("Campi valorizzati da fonti esterne", field_name_it(r.get("external_promoted_fields"))))
    if clean(r.get("external_promoted_sources")):
        evidence.append(("Fonti esterne utilizzate", dedup_pipe(r.get("external_promoted_sources"))))

    pills = []
    # Solo fonti linkabili. Le label devono essere nomi fonte, non categorie.
    pills += source_pills("MASE", r.get("mase_source_urls", ""), "MASE")
    pills += source_pills(r.get("contractor_or_partner", ""), r.get("contractor_source_urls", ""), "Contractor / partner")
    pills += source_pills(r.get("operator_sources", ""), "", "Operatore")
    pills += source_pills(r.get("mw_it_sources", ""), r.get("mw_it_source_urls", ""), "MW IT")
    pills += source_pills(r.get("thermal_mwt_sources", ""), r.get("thermal_mwt_source_urls", ""), "MWt")
    pills += source_pills(r.get("site_area_sources", ""), r.get("site_area_source_urls", ""), "Superficie")

    dedup = []
    seen = set()
    for p in pills:
        if p in seen:
            continue
        seen.add(p)
        dedup.append(p)

    return {
        "project": project,
        "subtitle": " · ".join(x for x in [clean(r.get("operator_or_main_subject")), location, q_label] if x and x != "Da identificare"),
        "operator": clean(r.get("operator_or_main_subject")),
        "proponent": clean(r.get("mase_proponent")),
        "contractor": clean(r.get("contractor_or_partner")),
        "status": status,
        "mwt": strip_unit(mwt_raw, "mwt"),
        "mw_it": strip_unit(mw_it_raw, "mw_it"),
        "site_area": strip_unit(area_raw, "area"),
        "quality": (q_label, q_cls, q_title),
        "location": location,
        "map_query": map_query,
        "action_links": "",
        "summary": [x for x in summary if x],
        "notes": notes,
        "evidence": evidence,
        "sources": " ".join(dedup) if dedup else '<span class="muted">Nessuna fonte linkabile disponibile.</span>',
    }

def dcm_evidence_items(value: str) -> list[tuple[str, str]]:
    # Non usare più summary_facts grezzi in inglese.
    # La funzione resta per compatibilità ma non viene usata direttamente.
    return []

def dcm_record_to_page(r: dict[str, str]) -> dict[str, object]:
    project = clean(r.get("proposed_project_name"))
    readiness = clean(r.get("readiness"))
    q_label, q_cls, q_title = quality_from_status(clean(r.get("draft_bucket")), readiness)

    address = clean(r.get("address"))
    city = clean(r.get("city"))
    location = address or city or "Da identificare"

    map_query = location if location != "Da identificare" else f"{project} data center Italia"

    dcm_url = clean(r.get("dcm_source_url"))
    maps_link = clean(r.get("google_maps_url")) or maps_url(map_query)

    actions = [
        f'<a class="btn maps" href="{esc(maps_link)}" target="_blank" rel="noopener">Apri in Google Maps</a>'
    ]
    if dcm_url:
        actions.append(f'<a class="btn" href="{esc(dcm_url)}" target="_blank" rel="noopener">DataCenterMap</a>')

    mw_it_raw = clean(r.get("it_power_mw"))
    mwt_raw = clean(r.get("thermal_power_mwt") or r.get("thermal_mwt"))
    area_raw = clean(r.get("site_area_m2"))

    summary = [
        f"Operatore individuato: {sentence(r.get('operator_or_main_subject'))}" if clean(r.get("operator_or_main_subject")) else "",
        f"Ubicazione commerciale censita: {sentence(city)}" if city else "",
        f"Stato indicato dalla fonte DataCenterMap: {sentence(translate_status(r.get('dcm_status')))}" if clean(r.get("dcm_status")) else "",
        f"Potenza termica censita: {value_with_unit(mwt_raw, 'MWt')}" if mwt_raw else "",
        f"Potenza IT censita: {value_with_unit(mw_it_raw, 'MW')}" if mw_it_raw else "",
        f"Superficie censita: {area_with_unit(area_raw)}" if area_raw else "",
        f"Proponente/soggetto autorizzativo individuato: {sentence(r.get('authorization_proponent'))}" if clean(r.get("authorization_proponent")) else "",
        "GC/contractor ancora da identificare." if clean(r.get("contractor_or_partner")).lower() in {"da identificare", "da verificare"} else f"GC/contractor o partner individuato: {sentence(r.get('contractor_or_partner'))}" if clean(r.get("contractor_or_partner")) else "",
    ]

    notes = []
    if clean(r.get("promotion_recommendation")):
        notes.append(clean(r.get("promotion_recommendation")))
    elif readiness == "existing_project_child_or_enrichment":
        notes.append("Non promuovere come nuovo master: usare come child facility, espansione o enrichment di progetto esistente.")
    if clean(r.get("contractor_or_partner")).lower() in {"da identificare", "da verificare"}:
        notes.append("Priorità informativa: identificare GC, EPC, impresa esecutrice o partner tecnico.")
    if clean(r.get("dcm_status")):
        notes.append(f"Lo stato DataCenterMap va letto come indicazione commerciale grezza: {translate_status(r.get('dcm_status'))}.")

    evidence = []
    if dcm_url:
        evidence.append(("DataCenterMap", f"Scheda DataCenterMap disponibile per {project}."))
    if clean(r.get("dcm_status")):
        evidence.append(("Stato fonte", f"La fonte DataCenterMap indica stato: {translate_status(r.get('dcm_status'))}."))
    if city:
        evidence.append(("Ubicazione", f"Il record è localizzato commercialmente su {city}."))
    if clean(r.get("authorization_proponent")):
        evidence.append(("Proponente", f"Soggetto/proponente indicato: {clean(r.get('authorization_proponent'))}."))
    if clean(r.get("confirmed_layers")):
        layers = " | ".join(layer_name_it(x) for x in split_pipe(r.get("confirmed_layers")))
        evidence.append(("Layer confermati", layers))
    if readiness == "existing_project_child_or_enrichment":
        evidence.append(("Classificazione", "Record da trattare come espansione, sotto-facility o arricchimento di un progetto/campus già censito."))
    elif readiness == "existing_operational_reference":
        evidence.append(("Classificazione", "Asset esistente o reference commerciale: non trattare come nuova pipeline."))
    elif readiness == "operator_confirmed_only":
        evidence.append(("Classificazione", "Progetto confermato dall’operatore, ma con riscontri pubblici ancora incompleti."))
    elif readiness == "partial_public_confirmation":
        evidence.append(("Classificazione", "Progetto con conferme pubbliche parziali, da completare con ulteriori verifiche."))

    source_html = clean(r.get("source_links"))
    pills = []
    if source_html:
        pos = 0
        for match in re.finditer(r"<([^<>]+)>", source_html):
            label = source_html[pos:match.start()].strip().strip("|").strip()
            url = match.group(1).strip()
            if label and url:
                pills.append(f'<a class="source-pill" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>')
            pos = match.end()
    if dcm_url:
        pills.append(f'<a class="source-pill" href="{esc(dcm_url)}" target="_blank" rel="noopener">DataCenterMap</a>')

    return {
        "project": project,
        "subtitle": " · ".join(x for x in [clean(r.get("operator_or_main_subject")), city, q_label] if x),
        "operator": clean(r.get("operator_or_main_subject")),
        "proponent": clean(r.get("authorization_proponent")),
        "contractor": clean(r.get("contractor_or_partner")),
        "status": translate_status(r.get("dcm_status")),
        "mwt": strip_unit(mwt_raw, "mwt"),
        "mw_it": strip_unit(mw_it_raw, "mw_it"),
        "site_area": strip_unit(area_raw, "area"),
        "quality": (q_label, q_cls, q_title),
        "location": location,
        "map_query": map_query,
        "action_links": " ".join(actions),
        "summary": [x for x in summary if x],
        "notes": notes,
        "evidence": evidence,
        "sources": " ".join(pills) if pills else '<span class="muted">Nessuna fonte linkabile disponibile.</span>',
    }

def render_page(page: dict[str, object]) -> str:
    q_label, q_cls, q_title = page["quality"]  # type: ignore[misc]
    generated = datetime.now().isoformat(timespec="seconds")

    action_links = clean(page.get("action_links"))
    if not action_links:
        action_links = f'<a class="btn maps" href="{esc(maps_url(clean(page.get("map_query"))))}" target="_blank" rel="noopener">Apri in Google Maps</a>'

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page.get("project"))} - Data Center Radar</title>
<style>
{CSS}
</style>
</head>
<body>
<header>
  <h1>{esc(page.get("project"))}</h1>
  <p>{esc(page.get("subtitle")) if clean(page.get("subtitle")) else "Scheda progetto"} · scheda generata il {esc(generated)}</p>
</header>
<main>
  <div class="nav">
    <a href="../index.html">← Torna alla dashboard principale</a>
    <span class="subtle">Data Center Radar</span>
  </div>

  <section class="panel">
    <div class="section-title">
      <h2>Dati principali</h2>
    </div>
    <div class="grid">
      {field_card("Operatore", clean(page.get("operator")))}
      {field_card("Proponente", clean(page.get("proponent")))}
      {field_card("GC / contractor", clean(page.get("contractor")))}
      {field_card("Stato fonte", clean(page.get("status")))}
      {field_card("MWt", clean(page.get("mwt")))}
      {field_card("MW IT", clean(page.get("mw_it")))}
      {field_card("Superficie m²", clean(page.get("site_area")))}
      {quality_card(q_label, q_cls, q_title)}
    </div>
  </section>

  <section class="panel location-card">
    <div class="section-title">
      <h2>Ubicazione</h2>
      <span class="location-address">{esc(page.get("location"))}</span>
    </div>
    <div class="actions">
      {action_links}
    </div>
    <div class="map-wrap">
      <iframe src="{esc(maps_embed(clean(page.get("map_query"))))}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </div>
  </section>

  <section class="two-col">
    <div class="panel content-card">
      <h2>Sintesi progetto</h2>
      {list_html(page.get("summary", []))}
    </div>

    <div class="panel content-card">
      <h2>Note operative</h2>
      {list_html(page.get("notes", []))}
    </div>
  </section>

  <section class="panel content-card">
    <h2>Evidenze disponibili</h2>
    {evidence_html(page.get("evidence", []))}
  </section>

  <section class="panel content-card">
    <h2>Fonti</h2>
    <p>{page.get("sources")}</p>
  </section>
</main>
</body>
</html>
"""


def cleanup(txt: str) -> str:
    replacements = {
        "S.r.l..": "S.r.l.",
        "S.R.L..": "S.R.L.",
        "Srl..": "Srl.",
        "S.p.A..": "S.p.A.",
        "S.p.a..": "S.p.a.",
        "SpA..": "SpA.",
        "SPA..": "SPA.",
        "Fonti ext..": "Fonti ext.",
        "Parziale..": "Parziale.",
        "OK..": "OK.",
        "—.": "—",
    }
    for old, new in replacements.items():
        txt = txt.replace(old, new)
    return "\n".join(line.rstrip() for line in txt.splitlines()) + "\n"


def load_pages() -> list[dict[str, object]]:
    pages = []

    if MASTER_JSON.exists():
        data = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
        if isinstance(data, list):
            pages.extend(master_record_to_page(r) for r in data)

    if DCM_CSV.exists():
        with DCM_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            pages.extend(dcm_record_to_page(r) for r in csv.DictReader(f))

    return pages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Scrive in docs/projects invece che nella preview")
    args = parser.parse_args()

    out_dir = APPLY_DIR if args.apply else PREVIEW_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = load_pages()
    seen_slugs: dict[str, int] = {}

    for page in pages:
        project = clean(page.get("project"))
        base_slug = slugify(project)
        slug = base_slug

        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{base_slug}-{seen_slugs[base_slug]}"
        else:
            seen_slugs[slug] = 1

        out = out_dir / f"{slug}.html"
        out.write_text(cleanup(render_page(page)), encoding="utf-8")
        print(f"[OK] Written {out}")

    print(f"[OK] Generated {len(pages)} project pages in {out_dir}")


if __name__ == "__main__":
    main()
