from __future__ import annotations

import csv
import html
import re
from pathlib import Path
from urllib.parse import quote_plus


INDEX_HTML = Path("docs/index.html")
CANDIDATES_CSV = Path("data/output/external_sources/datacentermap_promotion_draft.csv")
DCM_CURATED = Path("data/output/external_sources/datacentermap_candidates_curated.csv")


CITY_PROVINCE = {
    "Magenta": "MI",
    "Melegnano": "MI",
    "Segrate": "MI",
    "Arluno": "MI",
    "Cornaredo": "MI",
    "Corsico": "MI",
    "Milano": "MI",
    "Vellezzo Bellini": "PV",
    "Siziano": "PV",
}

READINESS_LABELS = {
    "ready_with_gc": "Pronto con GC",
    "ready_missing_gc": "Pronto, GC da identificare",
    "partial_public_confirmation": "Conferma pubblica parziale",
    "operator_confirmed_only": "Solo operatore confermato",
    "existing_project_child_or_enrichment": "Child/enrichment",
    "existing_operational_reference": "Asset esistente",
    "pending_validation": "Validazione pendente",
    "weak_or_no_public_evidence": "Evidenza debole",
    "not_validated": "Non validato",
}

BUCKET_ORDER = {
    "promotion_ready": 1,
    "near_ready": 2,
    "tracked_review": 3,
}


def clean(value: object) -> str:
    return str(value or "").strip()


def esc(value: object) -> str:
    return html.escape(clean(value), quote=True)


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", strip_tags(value)).strip()


def norm_text(value: str) -> str:
    value = normalize_text(value).lower()
    value = value.replace("à", "a").replace("è", "e").replace("é", "e")
    value = value.replace("ì", "i").replace("ò", "o").replace("ù", "u")
    return value


def norm_key(value: str) -> str:
    value = norm_text(value)
    value = value.replace("&", " and ")
    value = re.sub(r"\b(data center|campus|italy|italia|milan|milano)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_key(value))


def slugify(value: str) -> str:
    value = norm_text(value)
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def read_candidates() -> list[dict[str, str]]:
    if not CANDIDATES_CSV.exists():
        raise SystemExit(f"File candidati non trovato: {CANDIDATES_CSV}")

    with CANDIDATES_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    return sorted(
        rows,
        key=lambda r: (
            BUCKET_ORDER.get(clean(r.get("draft_bucket")), 99),
            clean(r.get("proposed_project_name")).lower(),
        ),
    )


def maps_url(row: dict[str, str]) -> str:
    url = clean(row.get("google_maps_url"))
    if url:
        return url

    address = clean(row.get("address"))
    if address:
        return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(address)

    name = clean(row.get("proposed_project_name"))
    city = clean(row.get("city"))
    query = " ".join(part for part in [name, city, "data center", "Italia"] if part)
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def map_icon(url: str, title: str = "Apri in Google Maps") -> str:
    return (
        f'<a class="map-icon" href="{esc(url)}" target="_blank" rel="noopener" '
        f'title="{esc(title)}" aria-label="{esc(title)}">&#128205;</a>'
    )


def dcm_pill(url: str) -> str:
    if not url:
        return '<span class="muted">DataCenterMap</span>'

    return f'<a class="link-pill" href="{esc(url)}" target="_blank" rel="noopener">DataCenterMap</a>'


def project_page_href(row: dict[str, str]) -> str:
    return f'projects/{slugify(clean(row.get("proposed_project_name")))}.html'


def display_mw(value: str) -> str:
    value = clean(value)
    value = re.sub(r"\s*MW\s*$", "", value, flags=re.I)
    return value or "—"


def display_area(value: str) -> str:
    value = clean(value)
    value = re.sub(r"\s*m²\s*$", "", value, flags=re.I)
    return value or "—"


def quality_status(row: dict[str, str]) -> tuple[str, str, str, str]:
    readiness = clean(row.get("readiness"))

    if readiness in {"ready_with_gc", "ready_missing_gc"}:
        return (
            "Consolidato",
            "OK",
            "grade-a",
            "Candidato DataCenterMap validato: pronto per review master.",
        )

    if readiness in {"partial_public_confirmation", "operator_confirmed_only"}:
        return (
            "Parziale",
            "Parziale",
            "grade-c",
            "Candidato DataCenterMap confermato ma con validazione pubblica incompleta.",
        )

    return (
        "Fonti esterne necessarie",
        "Fonti ext.",
        "grade-d",
        "Candidato da fonte esterna: utile per review, non promuovere automaticamente.",
    )


def quality_cell(row: dict[str, str]) -> str:
    _status, label, cls, title = quality_status(row)
    return f'<span class="badge {cls}" title="{esc(title)}">{esc(label)}</span>'


def source_cell(row: dict[str, str]) -> str:
    return dcm_pill(clean(row.get("dcm_source_url")))


def project_cell(row: dict[str, str]) -> str:
    name = clean(row.get("proposed_project_name"))
    readiness = clean(row.get("readiness"))
    href = project_page_href(row)

    return f'''
          <td class="project-cell">
            <a class="project-link" href="{esc(href)}"><strong>{esc(name)}</strong></a> {map_icon(maps_url(row))}
            <br><span class="muted">Fonte DataCenterMap</span>
            <br><span class="muted">{esc(READINESS_LABELS.get(readiness, readiness))}</span>
          </td>'''


def cell_for_header(header: str, row: dict[str, str]) -> str:
    h = norm_text(header)

    operator = clean(row.get("operator_or_main_subject"))
    proponent = clean(row.get("authorization_proponent"))
    contractor = clean(row.get("contractor_or_partner")) or "Da identificare"
    city = clean(row.get("city"))
    province = CITY_PROVINCE.get(city, "")
    dcm_status = clean(row.get("dcm_status"))
    readiness = clean(row.get("readiness"))
    it_power = clean(row.get("it_power_mw"))
    area = clean(row.get("site_area_m2"))

    if "progetto" in h or "project" in h or "nome" in h:
        return project_cell(row)

    if "operatore" in h or "developer" in h or "cliente" in h:
        return f"<td>{esc(operator) or '—'}</td>"

    if "proponente" in h or "autorizzativo" in h:
        return f"<td>{esc(proponent) or 'Da verificare'}</td>"

    if "realizzatore" in h or "partner" in h or "contractor" in h or "gc" in h:
        return f"<td>{esc(contractor)}</td>"

    if "comune" in h or "citta" in h:
        return f"<td>{esc(city) or '—'}</td>"

    if "provincia" in h or h == "pv":
        return f"<td>{esc(province) or '—'}</td>"

    if "regione" in h:
        return "<td>Lombardia</td>"

    if "stato" in h or "fase" in h:
        return (
            f"<td>{esc(dcm_status) or '—'}"
            f'<br><span class="muted">{esc(READINESS_LABELS.get(readiness, readiness))}</span></td>'
        )

    if "mw it" in h or "mw_it" in h or "potenza it" in h:
        return f'<td class="num">{esc(display_mw(it_power))}</td>'

    if "mwt" in h or "termic" in h:
        return '<td class="num">—</td>'

    if "superficie" in h or "area" in h or "m2" in h or "m²" in h:
        return f'<td class="num">{esc(display_area(area))}</td>'

    if "qualita" in h or "quality" in h:
        return f"<td>{quality_cell(row)}</td>"

    if "fonte" in h or "fonti" in h or "source" in h:
        return f'<td class="sources-cell">{source_cell(row)}</td>'

    if "priorita" in h or "priorità" in h:
        priority = "Alta" if clean(row.get("draft_bucket")) in {"promotion_ready", "near_ready"} else "Media"
        return f"<td>{priority}</td>"

    if h == "id" or "identificativo" in h:
        return "<td>DCM</td>"

    return "<td>—</td>"


def build_candidate_row(row: dict[str, str], headers: list[str]) -> str:
    name = clean(row.get("proposed_project_name"))
    operator = clean(row.get("operator_or_main_subject"))
    city = clean(row.get("city"))
    readiness = clean(row.get("readiness"))
    bucket = clean(row.get("draft_bucket"))
    dcm_status = clean(row.get("dcm_status"))

    status_value, _label, _cls, _title = quality_status(row)

    search = " ".join([
        name,
        operator,
        city,
        status_value,
        readiness,
        bucket,
        dcm_status,
        "DataCenterMap",
    ])

    cells = "\n".join(cell_for_header(h, row) for h in headers)

    return f'''
        <tr data-search="{esc(search)}" data-status="{esc(status_value)}">
{cells}
        </tr>'''


def extract_headers(table_html_before_tbody: str) -> list[str]:
    thead_match = re.search(r"<thead\b[^>]*>(.*?)</thead>", table_html_before_tbody, re.I | re.S)
    if not thead_match:
        return []

    headers = re.findall(r"<th\b[^>]*>(.*?)</th>", thead_match.group(1), re.I | re.S)
    return [normalize_text(h) for h in headers]


def fallback_cell_count(tbody_html: str) -> int:
    first_row = re.search(r"<tr\b[^>]*>(.*?)</tr>", tbody_html, re.I | re.S)
    if not first_row:
        return 10

    return len(re.findall(r"<td\b[^>]*>", first_row.group(1), re.I))


def fallback_headers(count: int) -> list[str]:
    base = [
        "Progetto",
        "Operatore",
        "Proponente",
        "Realizzatore / partner",
        "Comune",
        "Stato DCM raw",
        "MW IT",
        "Superficie",
        "Qualità dati",
        "Fonti",
    ]

    if count <= len(base):
        return base[:count]

    return base + [f"Extra {i}" for i in range(count - len(base))]


def find_immediate_tbody(txt: str) -> tuple[int, int, int, list[str]]:
    lower = txt.lower()

    marker_pos = lower.find("vista immediata")
    if marker_pos == -1:
        marker_pos = 0

    tbody_start = lower.find("<tbody", marker_pos)
    if tbody_start == -1:
        raise SystemExit("tbody non trovato dopo Vista immediata")

    tbody_open_end = lower.find(">", tbody_start)
    tbody_close = lower.find("</tbody>", tbody_open_end)

    if tbody_open_end == -1 or tbody_close == -1:
        raise SystemExit("tbody non valido")

    table_start = lower.rfind("<table", 0, tbody_start)
    if table_start == -1:
        raise SystemExit("table non trovata")

    before_tbody = txt[table_start:tbody_start]
    tbody_html = txt[tbody_open_end + 1:tbody_close]

    headers = extract_headers(before_tbody)
    if not headers:
        headers = fallback_headers(fallback_cell_count(tbody_html))

    return tbody_open_end + 1, tbody_close, table_start, headers


def split_rows(tbody: str) -> list[re.Match[str]]:
    return list(re.finditer(r"\s*<tr\b[^>]*>.*?</tr>\s*", tbody, flags=re.I | re.S))


def extract_cells_with_spans(row: str) -> list[tuple[int, int, str]]:
    return [
        (m.start(), m.end(), m.group(0))
        for m in re.finditer(r"<td\b[^>]*>.*?</td>", row, flags=re.I | re.S)
    ]


def find_header_index(headers: list[str], wanted: list[str]) -> int | None:
    lower_headers = [norm_text(h) for h in headers]
    for idx, h in enumerate(lower_headers):
        for token in wanted:
            if token in h:
                return idx
    return None


def extract_project_name(row: str) -> str:
    m = re.search(r"<strong>(.*?)</strong>", row, flags=re.I | re.S)
    if m:
        return normalize_text(m.group(1))

    cells = extract_cells_with_spans(row)
    if cells:
        return normalize_text(cells[0][2])

    return ""


def load_dcm_location_index() -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}

    if not DCM_CURATED.exists():
        return index

    with DCM_CURATED.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            facility = clean(r.get("facility_name"))
            if not facility or "You're in the Right Place" in facility:
                continue

            source_url = clean(r.get("source_url"))
            if source_url and "datacentermap.com" not in source_url:
                continue

            info = {
                "facility_name": facility,
                "matched_project": clean(r.get("matched_project_curated") or r.get("matched_project")),
                "address": clean(r.get("address")),
                "google_maps_url": clean(r.get("google_maps_url")),
                "source_url": source_url,
            }

            for key in [facility, info["matched_project"], clean(r.get("project"))]:
                if not key:
                    continue
                index[norm_key(key)] = info
                index[compact_key(key)] = info

    aliases = {
        "vantage mxp2": ["vantage mxp2 milan"],
        "cyrusone mil1": ["cyrusone mil1 milan"],
        "retelit avalon 3": ["retelit avalon 3"],
        "data4 cornaredo": ["data4 milan campus mil01", "data4 milan campus"],
        "equinix ml7 ml8": ["equinix ml7x"],
    }

    for master_name, alias_list in aliases.items():
        for alias in alias_list:
            info = index.get(norm_key(alias)) or index.get(compact_key(alias))
            if info:
                index[norm_key(master_name)] = info
                index[compact_key(master_name)] = info
                break

    return index


def find_dcm_match(project: str, index: dict[str, dict[str, str]]) -> dict[str, str] | None:
    if not project:
        return None

    direct = index.get(norm_key(project)) or index.get(compact_key(project))
    if direct:
        return direct

    p_compact = compact_key(project)
    if not p_compact:
        return None

    for key, info in index.items():
        if len(key) < 5:
            continue
        if p_compact in key or key in p_compact:
            return info

    return None


def add_project_map_icon(row: str, project: str, comune: str, info: dict[str, str] | None) -> str:
    if "map-icon" in row:
        return row

    if info and info.get("google_maps_url"):
        url = info["google_maps_url"]
    elif info and info.get("address"):
        url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(info["address"])
    else:
        query = " ".join(part for part in [project, comune, "data center", "Italia"] if part)
        url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)

    icon = map_icon(url)

    new_row, n = re.subn(
        r"(<a\b[^>]*class=\"project-link\"[^>]*>\s*<strong>.*?</strong>\s*</a>)",
        r"\1 " + icon,
        row,
        count=1,
        flags=re.I | re.S,
    )

    if n:
        return new_row

    new_row, n = re.subn(
        r"(<strong>.*?</strong>)",
        r"\1 " + icon,
        row,
        count=1,
        flags=re.I | re.S,
    )

    return new_row if n else row


def add_dcm_source_to_existing_row(row: str, headers: list[str], info: dict[str, str] | None) -> str:
    if not info or not info.get("source_url"):
        return row

    if "datacentermap.com" in row.lower():
        return row

    cells = extract_cells_with_spans(row)
    source_idx = find_header_index(headers, ["fonte", "fonti", "source"])

    if source_idx is None or source_idx >= len(cells):
        return row

    start, end, cell = cells[source_idx]
    insert = " " + dcm_pill(info["source_url"])
    new_cell = re.sub(r"</td>\s*$", insert + "</td>", cell, flags=re.I | re.S)

    return row[:start] + new_cell + row[end:]


def decorate_existing_row(row: str, headers: list[str], dcm_index: dict[str, dict[str, str]]) -> str:
    if "EXTERNAL_CANDIDATES" in row:
        return row

    project = extract_project_name(row)
    if not project:
        return row

    cells = extract_cells_with_spans(row)

    comune = ""
    comune_idx = find_header_index(headers, ["comune", "citta", "città"])
    if comune_idx is not None and comune_idx < len(cells):
        comune = normalize_text(cells[comune_idx][2])

    info = find_dcm_match(project, dcm_index)

    row = add_project_map_icon(row, project, comune, info)
    row = add_dcm_source_to_existing_row(row, headers, info)

    return row


def remove_existing_external_block(txt: str) -> str:
    patterns = [
        r"\n\s*<!-- EXTERNAL_CANDIDATES_DRAFT_START -->.*?<!-- EXTERNAL_CANDIDATES_DRAFT_END -->\s*\n",
        r"\n\s*<!-- EXTERNAL_CANDIDATES_START -->.*?<!-- EXTERNAL_CANDIDATES_END -->\s*\n",
    ]

    for pattern in patterns:
        txt = re.sub(pattern, "\n", txt, flags=re.I | re.S)

    return txt


def rename_proponente_header(txt: str) -> str:
    return re.sub(
        r"(<th\b[^>]*>)\s*PROPONENTE\s+MASE\s*(</th>)",
        r"\1PROPONENTE\2",
        txt,
        flags=re.I,
    )


def inject_css(txt: str) -> str:
    css = r'''
.map-icon {
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:22px;
  height:22px;
  border-radius:999px;
  background:#ecfdf3;
  color:#166534;
  text-decoration:none;
  font-size:14px;
  font-weight:900;
  margin-left:4px;
  vertical-align:middle;
}
.map-icon:hover {
  filter:brightness(.96);
}
tbody tr:nth-child(odd) td {
  background:#ffffff;
}
tbody tr:nth-child(even) td {
  background:#f8fafc;
}
tbody tr:hover td {
  background:#eff6ff;
}
'''

    if ".map-icon" in txt and "tbody tr:nth-child(odd)" in txt:
        return txt

    return txt.replace("</style>", css + "\n</style>")


def inject_candidates(txt: str, rows: list[dict[str, str]]) -> str:
    tbody_start, tbody_close, _table_start, headers = find_immediate_tbody(txt)

    tbody_html = txt[tbody_start:tbody_close]
    candidates_html = "\n".join(build_candidate_row(r, headers) for r in rows)

    block = f'''
        <!-- EXTERNAL_CANDIDATES_START -->
{candidates_html}
        <!-- EXTERNAL_CANDIDATES_END -->
'''

    return txt[:tbody_close] + block + txt[tbody_close:]


def decorate_existing_rows(txt: str, dcm_index: dict[str, dict[str, str]]) -> str:
    tbody_start, tbody_close, _table_start, headers = find_immediate_tbody(txt)
    tbody = txt[tbody_start:tbody_close]

    rebuilt = ""
    cursor = 0

    for match in split_rows(tbody):
        rebuilt += tbody[cursor:match.start()]
        rebuilt += decorate_existing_row(match.group(0), headers, dcm_index)
        cursor = match.end()

    rebuilt += tbody[cursor:]

    return txt[:tbody_start] + rebuilt + txt[tbody_close:]


def parse_number_it(value: str) -> float:
    value = normalize_text(value)
    value = re.sub(r"[^\d,.-]", "", value)

    if not value:
        return 0.0

    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0.0


def format_number_it(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return f"{round(value):,}".replace(",", ".")

    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def table_stats(txt: str) -> dict[str, str]:
    tbody_start, tbody_close, _table_start, headers = find_immediate_tbody(txt)
    tbody = txt[tbody_start:tbody_close]

    rows = [m.group(0) for m in split_rows(tbody)]

    quality_idx = find_header_index(headers, ["qualita", "qualità", "quality"])
    priority_idx = find_header_index(headers, ["priorita", "priorità"])
    contractor_idx = find_header_index(headers, ["contractor", "partner", "realizzatore"])
    mw_it_idx = find_header_index(headers, ["mw it", "potenza it", "mw_it"])
    mwt_idx = find_header_index(headers, ["mwt", "termic"])
    area_idx = find_header_index(headers, ["superficie", "area", "m2", "m²"])

    total = 0
    high_priority = 0
    ok = 0
    partial = 0
    external = 0
    contractor_known = 0
    mw_it_total = 0.0
    mwt_total = 0.0
    area_known = 0

    for row in rows:
        cells = [c for _s, _e, c in extract_cells_with_spans(row)]
        if not cells:
            continue

        total += 1
        row_raw = html.unescape(row).lower()
        row_txt = norm_text(row)

        # Priorità: usa sia cella dedicata sia data-search/raw HTML.
        priority_blob = ""
        if priority_idx is not None and priority_idx < len(cells):
            priority_blob = norm_text(cells[priority_idx])

        if re.search(r"\balta\b", priority_blob) or re.search(r"\balta\b", row_raw):
            high_priority += 1

        # Qualità dati.
        quality_blob = ""
        if quality_idx is not None and quality_idx < len(cells):
            quality_blob = norm_text(cells[quality_idx])
        else:
            quality_blob = row_txt

        if "fonti" in quality_blob:
            external += 1
        elif "parziale" in quality_blob:
            partial += 1
        elif re.search(r"\bok\b", quality_blob) or "consolidato" in quality_blob:
            ok += 1

        # Contractor/partner noto.
        if contractor_idx is not None and contractor_idx < len(cells):
            contractor_value = norm_text(cells[contractor_idx])
            if (
                contractor_value
                and "da identificare" not in contractor_value
                and contractor_value != "—"
                and contractor_value != "-"
            ):
                contractor_known += 1

        # MW IT.
        if mw_it_idx is not None and mw_it_idx < len(cells):
            mw_it_total += parse_number_it(cells[mw_it_idx])

        # MWt: colonna distinta, non deve ereditare MW IT.
        if mwt_idx is not None and mwt_idx < len(cells):
            mwt_total += parse_number_it(cells[mwt_idx])

        # Superficie nota: conta record con area valorizzata.
        if area_idx is not None and area_idx < len(cells):
            if parse_number_it(cells[area_idx]) > 0:
                area_known += 1

    return {
        "total": str(total),
        "high_priority": str(high_priority),
        "ok": str(ok),
        "partial": str(partial),
        "external": str(external),
        "contractor_known": str(contractor_known),
        "mw_it_total": format_number_it(mw_it_total),
        "mwt_total": format_number_it(mwt_total),
        "area_known": str(area_known),
    }



def update_kpis(txt: str) -> str:
    stats = table_stats(txt)

    pattern = re.compile(
        r'(<div class="kpi-label">(?P<label>.*?)</div>\s*<div class="kpi-value">)(?P<value>.*?)(</div>)',
        re.I | re.S,
    )

    def repl(m: re.Match[str]) -> str:
        label = norm_text(m.group("label"))
        new_value: str | None = None

        if "priorit" in label and "alta" in label:
            new_value = stats["high_priority"]
        elif "mwt" in label:
            new_value = stats["mwt_total"]
        elif "mw it" in label or "mw noto" in label or "mw" in label:
            new_value = stats["mw_it_total"]
        elif "contractor" in label or "partner" in label:
            new_value = stats["contractor_known"]
        elif "superficie" in label or "area" in label:
            new_value = stats["area_known"]
        elif "fonti" in label:
            new_value = stats["external"]
        elif "parzial" in label or "verificare" in label:
            new_value = stats["partial"]
        elif "consolidat" in label or label == "ok":
            new_value = stats["ok"]
        elif "progett" in label or "total" in label or "totale" in label:
            new_value = stats["total"]

        if new_value is None:
            return m.group(0)

        return m.group(1) + esc(new_value) + m.group(4)

    return pattern.sub(repl, txt)



def main() -> None:
    if not INDEX_HTML.exists():
        raise SystemExit(f"Homepage non trovata: {INDEX_HTML}")

    rows = read_candidates()
    dcm_index = load_dcm_location_index()

    txt = INDEX_HTML.read_text(encoding="utf-8")
    txt = remove_existing_external_block(txt)
    txt = rename_proponente_header(txt)
    txt = inject_css(txt)
    txt = decorate_existing_rows(txt, dcm_index)
    txt = inject_candidates(txt, rows)
    txt = update_kpis(txt)

    txt = "\n".join(line.rstrip() for line in txt.splitlines()) + "\n"

    INDEX_HTML.write_text(txt, encoding="utf-8")

    print(f"[OK] Promoted {len(rows)} DataCenterMap candidates into {INDEX_HTML}")
    print(f"[OK] DataCenterMap location index entries: {len(dcm_index)}")
    print("[OK] Added Google Maps pin to existing Vista immediata rows")
    print("[OK] Updated homepage KPI statistics")


if __name__ == "__main__":
    main()
