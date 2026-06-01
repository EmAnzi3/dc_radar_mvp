from __future__ import annotations

import csv
import html
import re
from datetime import datetime
from pathlib import Path


MASTER = Path("data/output/dc_project_fused_master.csv")
EXTERNAL_FACTS = Path("data/output/external_sources/external_facts_review.csv")
REGIONAL_CURATED = Path("data/output/external_sources/regional_environmental_candidates_curated.csv")

OUT_PROPOSALS = Path("data/output/external_sources/external_merge_proposals.csv")
OUT_HOME = Path("reports/site/external_sources/draft_homepage_external_review.html")
OUT_PROJECTS = Path("reports/site/external_sources/draft_projects")


FIELD_CANDIDATES = {
    "operator": ["operator_or_main_subject", "operator", "developer"],
    "mase_proponent": ["mase_proponent", "primary_proponent", "primary_developer"],
    "contractor_or_partner": ["contractor_or_partner", "contractor", "realizzatore"],
    "mw_it": ["mw_it", "primary_it_power_mw", "it_power_mw"],
    "thermal_power_mwt": ["thermal_power_mwt", "primary_thermal_power_mwt"],
    "site_area_m2": ["site_area_m2", "primary_site_area_m2", "area_m2"],
    "location": ["location", "municipality", "municipality_or_area"],
    "region": ["region"],
    "business_status": ["business_status", "quality_status", "status"],
}


HOMEPAGE_FACT_MAP = {
    "contractor_or_partner": "contractor_or_partner",
    "it_power_mw": "mw_it",
    "thermal_power_mwt": "thermal_mwt",
}


PROJECT_PAGE_FACT_TYPES = {
    "contractor_or_partner",
    "contractor_role",
    "engineering_design",
    "works_direction",
    "heat_reuse",
    "it_power_mw",
    "thermal_power_mwt",
    "area_m2",
    "data_halls",
    "project_status_or_timing",
    "local_authority_evidence",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: object) -> str:
    value = norm(value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def esc(value: object) -> str:
    return html.escape(clean(value))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_pipe(value: object) -> list[str]:
    out = []

    for part in clean(value).split("|"):
        part = clean(part)
        if part and part not in out:
            out.append(part)

    return out


def add_unique(target: list[str], value: object) -> None:
    value = clean(value)
    if value and value not in target:
        target.append(value)


def is_missing(value: object) -> bool:
    v = norm(value)

    return v in {
        "",
        "-",
        "—",
        "n a",
        "na",
        "none",
        "null",
        "nan",
        "da identificare",
        "da verificare",
        "non disponibile",
        "not available",
        "unknown",
        "tbd",
    }


def first_existing(row: dict[str, str], logical_field: str) -> str:
    for field in FIELD_CANDIDATES.get(logical_field, [logical_field]):
        value = clean(row.get(field))
        if value:
            return value

    return ""


def source_links(source_urls: str, limit: int = 3) -> str:
    links = []

    for idx, url in enumerate(split_pipe(source_urls)[:limit], start=1):
        links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">fonte {idx}</a>')

    return " ".join(links) if links else "—"


def load_external_by_project() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}

    for row in read_csv(EXTERNAL_FACTS):
        project = clean(row.get("project"))
        if not project:
            continue

        grouped.setdefault(project, []).append(row)

    return grouped


def load_regional_by_project() -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
    by_project: dict[str, list[dict[str, str]]] = {}
    references = []

    for row in read_csv(REGIONAL_CURATED):
        project = clean(row.get("matched_project"))
        status = clean(row.get("curated_status"))

        if project:
            by_project.setdefault(project, []).append(row)
        elif status == "reference_policy_review":
            references.append(row)

    return by_project, references


def facts_for_type(rows: list[dict[str, str]], fact_type: str, statuses: set[str] | None = None) -> list[dict[str, str]]:
    out = []

    for row in rows:
        if clean(row.get("fact_type")) != fact_type:
            continue

        if statuses and clean(row.get("review_status")) not in statuses:
            continue

        out.append(row)

    return out


def values_from_facts(rows: list[dict[str, str]]) -> list[str]:
    values = []

    for row in rows:
        value = clean(row.get("fact_value"))

        if is_missing(value):
            continue

        add_unique(values, value)

    return values


def best_source_summary(rows: list[dict[str, str]]) -> tuple[str, str]:
    sources = []
    urls = []

    for row in rows:
        for s in split_pipe(row.get("sources")):
            add_unique(sources, s)

        for u in split_pipe(row.get("source_urls")):
            add_unique(urls, u)

    return " | ".join(sources), " | ".join(urls)


def is_real_improvement(old_value: object, proposed_value: object) -> bool:
    old_missing = is_missing(old_value)
    new_missing = is_missing(proposed_value)

    if new_missing:
        return False

    if old_missing:
        return True

    return norm(old_value) != norm(proposed_value)


def proposal_row(
    project: str,
    target_field: str,
    old_value: str,
    proposed_value: str,
    proposal_scope: str,
    source_rows: list[dict[str, str]],
    reason: str,
) -> dict[str, str]:
    sources, urls = best_source_summary(source_rows)

    statuses = []
    fact_types = []

    for row in source_rows:
        add_unique(statuses, row.get("review_status"))
        add_unique(fact_types, row.get("fact_type"))

    return {
        "project": project,
        "target_field": target_field,
        "old_value": old_value,
        "proposed_value": proposed_value,
        "proposal_scope": proposal_scope,
        "external_review_status": " | ".join(statuses),
        "external_fact_types": " | ".join(fact_types),
        "sources": sources,
        "source_urls": urls,
        "reason": reason,
        "apply_to_master": "no",
    }


def qualified_area_proposal(project: str, area_rows: list[dict[str, str]]) -> tuple[str, list[dict[str, str]], str, str]:
    values = values_from_facts(area_rows)

    if not values:
        return "", [], "", ""

    # Caso pulito: una sola superficie candidata.
    if len(values) == 1:
        return (
            values[0],
            area_rows,
            "homepage_and_project_page",
            "Superficie assente nel master; valore esterno unico disponibile.",
        )

    # Caso Retelit Avalon 3:
    # 13.000 m² = Avalon Campus / area complessiva
    # 3.500 m²  = Avalon 3 / superficie costruita
    # In homepage usiamo il formato già adottato per altri progetti:
    # area principale (superficie costruita tra parentesi).
    if project == "Retelit Avalon 3":
        has_campus = any(clean(r.get("fact_value")) == "13.000 m²" for r in area_rows)
        has_built = any(clean(r.get("fact_value")) == "3.500 m²" for r in area_rows)

        if has_campus and has_built:
            return (
                "13.000 (3.500 sup. costruita)",
                area_rows,
                "homepage_and_project_page",
                "Area campus/Avalon Campus con superficie costruita Avalon 3 tra parentesi.",
            )

    # Default prudente: mostra in draft, ma non come valore tabellare definitivo.
    return (
        " | ".join(values),
        area_rows,
        "homepage_draft_review_only",
        "Superficie assente; valori esterni disponibili ma da qualificare semanticamente.",
    )


def project_page_values(project: str, fact_type: str, fact_rows: list[dict[str, str]]) -> list[str]:
    values = values_from_facts(fact_rows)

    if fact_type == "local_authority_evidence":
        if project == "Apto Lacchiarella":
            return ["Evidenza Comune/Albo Lacchiarella su progetto data center"]

        if project == "Stack Campus Siziano":
            return ["STACK EMEA ITALY SRL - nuovo data center via Marche 8 / Commissione Paesaggio"]

        # Scarta liste keyword pure e tieni solo frasi leggibili.
        readable = []
        for value in values:
            nv = norm(value)
            if nv in {"data center", "apto", "apto italia", "stack", "stack emea italy", "via marche 8", "impianti tecnici"}:
                continue
            add_unique(readable, value)

        return readable or values

    return values


def regional_match_values(project: str, regional_rows: list[dict[str, str]]) -> list[str]:
    values = []

    for row in regional_rows:
        region = clean(row.get("region"))
        source_type = clean(row.get("source_type"))
        strong_terms = clean(row.get("strong_terms"))

        if project == "Aruba Roma Tecnopolo Tiburtino":
            add_unique(values, "Regione Lazio VIA - match su Aruba Roma Tecnopolo Tiburtino")

        elif strong_terms:
            add_unique(values, f"{region} {source_type} - {strong_terms}")

    return values


def build_project_draft(row: dict[str, str], external_rows: list[dict[str, str]], regional_rows: list[dict[str, str]]) -> dict[str, object]:
    project = clean(row.get("project"))

    current = {
        "operator": first_existing(row, "operator"),
        "mase_proponent": first_existing(row, "mase_proponent"),
        "contractor_or_partner": first_existing(row, "contractor_or_partner"),
        "mw_it": first_existing(row, "mw_it"),
        "thermal_power_mwt": first_existing(row, "thermal_power_mwt"),
        "site_area_m2": first_existing(row, "site_area_m2"),
        "location": first_existing(row, "location"),
        "region": first_existing(row, "region"),
        "business_status": first_existing(row, "business_status"),
    }

    proposals = []

    # Campi che possono finire anche in homepage se mancanti.
    for fact_type, target_field in HOMEPAGE_FACT_MAP.items():
        fact_rows = facts_for_type(
            external_rows,
            fact_type,
            statuses={"ready_for_review"},
        )
        values = values_from_facts(fact_rows)

        if not values:
            continue

        old_value = current.get(target_field, "")
        proposed_value = " | ".join(values)

        # Homepage: proponi solo se il campo master è realmente assente.
        # Se il valore esiste già, la fonte esterna resta utile come evidenza in scheda,
        # ma non deve generare una falsa proposta solo per formattazione diversa.
        if is_missing(old_value) and is_real_improvement(old_value, proposed_value):
            proposals.append(
                proposal_row(
                    project=project,
                    target_field=target_field,
                    old_value=old_value,
                    proposed_value=proposed_value,
                    proposal_scope="homepage_and_project_page",
                    source_rows=fact_rows,
                    reason="Campo mancante nel master; fonte esterna pronta per review.",
                )
            )

    # Superfici: se il valore è qualificabile, può finire anche in homepage.
    area_rows = facts_for_type(
        external_rows,
        "area_m2",
        statuses={"needs_semantic_qualification", "ready_for_review", "review_required"},
    )

    proposed_area, area_source_rows, area_scope, area_reason = qualified_area_proposal(project, area_rows)

    if proposed_area and is_missing(current.get("site_area_m2")):
        if is_real_improvement(current.get("site_area_m2", ""), proposed_area):
            proposals.append(
                proposal_row(
                    project=project,
                    target_field="site_area_m2",
                    old_value=current.get("site_area_m2", ""),
                    proposed_value=proposed_area,
                    proposal_scope=area_scope,
                    source_rows=area_source_rows,
                    reason=area_reason,
                )
            )

    # Facts utili solo in scheda progetto.
    for fact_type in sorted(PROJECT_PAGE_FACT_TYPES - set(HOMEPAGE_FACT_MAP.keys()) - {"area_m2"}):
        fact_rows = facts_for_type(
            external_rows,
            fact_type,
            statuses={"ready_for_review", "review_required", "needs_semantic_qualification"},
        )
        values = project_page_values(project, fact_type, fact_rows)

        if not values:
            continue

        proposals.append(
            proposal_row(
                project=project,
                target_field=f"project_page::{fact_type}",
                old_value="",
                proposed_value=" | ".join(values),
                proposal_scope="project_page_only",
                source_rows=fact_rows,
                reason="Fatto utile per sezione evidenze esterne della scheda progetto.",
            )
        )

    # Regionali: match noto in scheda progetto.
    if regional_rows:
        source_rows = []
        for rr in regional_rows:
            source_rows.append({
                "review_status": clean(rr.get("curated_status")),
                "fact_type": "regional_environmental_match",
                "sources": clean(rr.get("source_system")),
                "source_urls": clean(rr.get("source_url")),
            })

        proposals.append(
            proposal_row(
                project=project,
                target_field="project_page::regional_environmental_match",
                old_value="",
                proposed_value=" | ".join(regional_match_values(project, regional_rows)),
                proposal_scope="project_page_only",
                source_rows=source_rows,
                reason="Match regionale VIA/VAS o fonte regionale utile per arricchire scheda progetto.",
            )
        )

    draft = dict(current)

    for p in proposals:
        target = p["target_field"]

        if p["proposal_scope"] in {"homepage_and_project_page", "homepage_draft_review_only"} and target in draft:
            draft[target] = p["proposed_value"]

    return {
        "project": project,
        "current": current,
        "draft": draft,
        "proposals": proposals,
        "external_rows": external_rows,
        "regional_rows": regional_rows,
    }


def value_cell(old: str, new: str, scope: str = "") -> str:
    old = clean(old)
    new = clean(new)

    if is_missing(old) and is_missing(new):
        return "—"

    if is_missing(old) and not is_missing(new):
        return f'<div class="new-value">{esc(new)}</div><div class="old-value">prima: vuoto / da identificare</div>'

    if not is_missing(new) and norm(old) != norm(new):
        label = "review" if "review" in scope else "new"
        return f'<div class="new-value">{esc(new)}</div><div class="old-value">prima: {esc(old)}</div><span class="mini">{esc(label)}</span>'

    return esc(old) if not is_missing(old) else "—"


def render_home(project_drafts: list[dict[str, object]], references: list[dict[str, str]]) -> str:
    rows = []

    for d in project_drafts:
        project = clean(d["project"])
        current = d["current"]  # type: ignore[assignment]
        draft = d["draft"]  # type: ignore[assignment]
        proposals = d["proposals"]  # type: ignore[assignment]

        homepage_props = [
            p for p in proposals
            if p["proposal_scope"] in {"homepage_and_project_page", "homepage_draft_review_only"}
        ]

        project_props = [
            p for p in proposals
            if p["proposal_scope"] == "project_page_only"
        ]

        slug = slugify(project)
        page_link = f"draft_projects/{slug}.html"

        rows.append(f"""
        <tr>
          <td><a class="project-link" href="{esc(page_link)}">{esc(project)}</a></td>
          <td>{esc(draft.get("operator", ""))}</td>
          <td>{esc(draft.get("mase_proponent", ""))}</td>
          <td>{value_cell(current.get("contractor_or_partner", ""), draft.get("contractor_or_partner", ""))}</td>
          <td>{value_cell(current.get("mw_it", ""), draft.get("mw_it", ""))}</td>
          <td>{value_cell(current.get("thermal_power_mwt", ""), draft.get("thermal_power_mwt", ""))}</td>
          <td>{value_cell(current.get("site_area_m2", ""), draft.get("site_area_m2", ""), "review")}</td>
          <td>{esc(draft.get("location", ""))}</td>
          <td>{len(homepage_props)}</td>
          <td>{len(project_props)}</td>
        </tr>
        """)

    ref_rows = []

    for r in references:
        ref_rows.append(f"""
        <tr>
          <td>{esc(r.get("region"))}</td>
          <td>{esc(r.get("source_type"))}</td>
          <td>{esc(r.get("strong_terms"))}</td>
          <td><a href="{esc(r.get("source_url"))}" target="_blank" rel="noopener">apri</a></td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Draft Homepage · External Review</title>
<style>
:root {{
  --bg:#f5f7fb;
  --card:#ffffff;
  --text:#172033;
  --muted:#667085;
  --blue:#0f4c81;
  --green:#166534;
  --orange:#92400e;
  --border:#dfe4ea;
}}
body {{
  margin:0;
  font-family:Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}}
header {{
  background:linear-gradient(135deg,#08111f,#0f4c81);
  color:white;
  padding:26px 32px;
}}
main {{
  max-width:1600px;
  margin:0 auto;
  padding:20px;
}}
.panel {{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  padding:16px;
  margin-bottom:18px;
  overflow:auto;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
}}
table {{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}}
th,td {{
  border-bottom:1px solid #e5e7eb;
  padding:8px;
  vertical-align:top;
  text-align:left;
}}
th {{
  position:sticky;
  top:0;
  background:#f8fafc;
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
  z-index:2;
}}
a {{
  color:var(--blue);
  font-weight:800;
  text-decoration:none;
}}
.project-link {{
  color:#0f172a;
}}
.new-value {{
  color:var(--green);
  font-weight:900;
}}
.old-value {{
  color:var(--muted);
  font-size:11px;
  margin-top:2px;
}}
.mini {{
  display:inline-block;
  margin-top:3px;
  padding:2px 6px;
  border-radius:999px;
  background:#fff7ed;
  color:var(--orange);
  font-size:10px;
  font-weight:800;
  text-transform:uppercase;
}}
.note {{
  color:#dbeafe;
  max-width:900px;
}}
</style>
</head>
<body>
<header>
<h1>Draft Homepage · External Review</h1>
<p class="note">Vista comparativa: valori attuali + valori proposti da fonti esterne. Nessun dato viene applicato al master.</p>
<p class="note">Generato il {esc(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="panel">
<h2>Homepage draft comparativa</h2>
<table>
<thead>
<tr>
<th>Progetto</th>
<th>Operatore</th>
<th>Proponente</th>
<th>Realizzatore / partner</th>
<th>MW IT</th>
<th>MWt</th>
<th>Area m²</th>
<th>Località</th>
<th>Δ Homepage</th>
<th>Facts scheda</th>
</tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</section>

<section class="panel">
<h2>Reference regionali / policy</h2>
<table>
<thead>
<tr><th>Regione</th><th>Tipo</th><th>Termini</th><th>Fonte</th></tr>
</thead>
<tbody>
{''.join(ref_rows) if ref_rows else '<tr><td colspan="4">Nessuna reference regionale.</td></tr>'}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def render_project_page(d: dict[str, object]) -> str:
    project = clean(d["project"])
    current = d["current"]  # type: ignore[assignment]
    draft = d["draft"]  # type: ignore[assignment]
    proposals = d["proposals"]  # type: ignore[assignment]
    external_rows = d["external_rows"]  # type: ignore[assignment]
    regional_rows = d["regional_rows"]  # type: ignore[assignment]

    main_fields = [
        ("Realizzatore / partner", "contractor_or_partner"),
        ("MW IT", "mw_it"),
        ("MWt", "thermal_power_mwt"),
        ("Area m²", "site_area_m2"),
        ("Operatore", "operator"),
        ("Proponente", "mase_proponent"),
        ("Località", "location"),
        ("Regione", "region"),
    ]

    field_rows = []

    for label, key in main_fields:
        field_rows.append(f"""
        <tr>
          <td>{esc(label)}</td>
          <td>{esc(current.get(key, "")) or "—"}</td>
          <td>{value_cell(current.get(key, ""), draft.get(key, ""))}</td>
        </tr>
        """)

    prop_rows = []

    for p in proposals:
        prop_rows.append(f"""
        <tr>
          <td>{esc(p["proposal_scope"])}</td>
          <td>{esc(p["target_field"])}</td>
          <td>{esc(p["old_value"]) or "—"}</td>
          <td><strong>{esc(p["proposed_value"])}</strong></td>
          <td>{esc(p["external_review_status"])}</td>
          <td>{esc(p["sources"])}</td>
          <td>{source_links(p["source_urls"])}</td>
          <td>{esc(p["reason"])}</td>
        </tr>
        """)

    ext_rows = []

    for r in external_rows:
        ext_rows.append(f"""
        <tr>
          <td>{esc(r.get("source_layer"))}</td>
          <td>{esc(r.get("fact_type"))}</td>
          <td><strong>{esc(r.get("fact_value"))}</strong></td>
          <td>{esc(r.get("review_status"))}</td>
          <td>{esc(r.get("sources"))}</td>
          <td>{source_links(r.get("source_urls", ""))}</td>
          <td>{esc(r.get("usage_note"))}</td>
        </tr>
        """)

    reg_rows = []

    for r in regional_rows:
        reg_rows.append(f"""
        <tr>
          <td>{esc(r.get("region"))}</td>
          <td>{esc(r.get("curated_status"))}</td>
          <td>{esc(r.get("strong_terms"))}</td>
          <td>{esc(r.get("support_terms"))}</td>
          <td><a href="{esc(r.get("source_url"))}" target="_blank" rel="noopener">apri</a></td>
          <td>{esc(r.get("snippet"))}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{esc(project)} · External Draft</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1500px; margin:0 auto; padding:20px; }}
.panel {{ background:white; border:1px solid #dfe4ea; border-radius:14px; padding:16px; margin-bottom:18px; overflow:auto; box-shadow:0 8px 22px rgba(15,23,42,.07); }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; vertical-align:top; text-align:left; }}
th {{ color:#667085; font-size:11px; text-transform:uppercase; background:#f8fafc; }}
a {{ color:#0f4c81; font-weight:800; text-decoration:none; }}
.new-value {{ color:#166534; font-weight:900; }}
.old-value {{ color:#667085; font-size:11px; margin-top:2px; }}
.back {{ color:#dbeafe; }}
</style>
</head>
<body>
<header>
<p><a class="back" href="../draft_homepage_external_review.html">← torna alla draft homepage</a></p>
<h1>{esc(project)}</h1>
<p>Draft scheda progetto con evidenze esterne. Nessuna modifica applicata al master.</p>
</header>
<main>
<section class="panel">
<h2>Confronto campi principali</h2>
<table>
<thead><tr><th>Campo</th><th>Attuale</th><th>Draft esterno</th></tr></thead>
<tbody>{''.join(field_rows)}</tbody>
</table>
</section>

<section class="panel">
<h2>Proposte di integrazione</h2>
<table>
<thead>
<tr><th>Scope</th><th>Target</th><th>Attuale</th><th>Proposto</th><th>Status</th><th>Fonti</th><th>Link</th><th>Motivo</th></tr>
</thead>
<tbody>{''.join(prop_rows) if prop_rows else '<tr><td colspan="8">Nessuna proposta esterna.</td></tr>'}</tbody>
</table>
</section>

<section class="panel">
<h2>Facts esterni disponibili</h2>
<table>
<thead>
<tr><th>Layer</th><th>Tipo</th><th>Valore</th><th>Status</th><th>Fonti</th><th>Link</th><th>Uso</th></tr>
</thead>
<tbody>{''.join(ext_rows) if ext_rows else '<tr><td colspan="7">Nessun fact esterno.</td></tr>'}</tbody>
</table>
</section>

<section class="panel">
<h2>Fonti regionali / VIA / VAS</h2>
<table>
<thead>
<tr><th>Regione</th><th>Status</th><th>Strong</th><th>Support</th><th>URL</th><th>Snippet</th></tr>
</thead>
<tbody>{''.join(reg_rows) if reg_rows else '<tr><td colspan="6">Nessun match regionale.</td></tr>'}</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    master_rows = read_csv(MASTER)
    external_by_project = load_external_by_project()
    regional_by_project, regional_references = load_regional_by_project()

    project_drafts = []
    all_proposals = []

    OUT_PROJECTS.mkdir(parents=True, exist_ok=True)

    for row in master_rows:
        project = clean(row.get("project"))
        if not project:
            continue

        d = build_project_draft(
            row=row,
            external_rows=external_by_project.get(project, []),
            regional_rows=regional_by_project.get(project, []),
        )

        project_drafts.append(d)
        all_proposals.extend(d["proposals"])  # type: ignore[arg-type]

        project_page = OUT_PROJECTS / f"{slugify(project)}.html"
        project_page.write_text(render_project_page(d), encoding="utf-8")

    OUT_HOME.parent.mkdir(parents=True, exist_ok=True)
    OUT_HOME.write_text(render_home(project_drafts, regional_references), encoding="utf-8")

    fields = [
        "project",
        "target_field",
        "old_value",
        "proposed_value",
        "proposal_scope",
        "external_review_status",
        "external_fact_types",
        "sources",
        "source_urls",
        "reason",
        "apply_to_master",
    ]

    write_csv(OUT_PROPOSALS, all_proposals, fields)

    print(f"[OK] Written {OUT_PROPOSALS} with {len(all_proposals)} proposals")
    print(f"[OK] Written {OUT_HOME}")
    print(f"[OK] Written {OUT_PROJECTS} project draft pages")


if __name__ == "__main__":
    main()
