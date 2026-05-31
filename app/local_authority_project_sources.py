from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus


INPUT = Path("data/output/dc_enrichment_matrix.csv")
OUTPUT = Path("data/output/local_authority_project_sources.csv")
TOP_OUTPUT = Path("data/output/local_authority_top_queries.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean(value: object) -> str:
    return str(value or "").strip()


def norm_space(value: str) -> str:
    return re.sub(r"\s+", " ", clean(value)).strip()


LOCATION_OVERRIDES = {
    "data4 cornnaredo": ["Cornaredo", "Settimo Milanese"],
    "data4 cornaredo": ["Cornaredo", "Settimo Milanese"],
    "cyrusone mil1": ["Segrate", "Milano"],
    "retelit avalon 3": ["Milano"],
    "rom1": ["Roma"],
}


def google_url(query: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(query)


def make_row(
    project: str,
    developer: str,
    contractor: str,
    location: str,
    region: str,
    source_level: str,
    source_name: str,
    query: str,
    purpose: str,
    priority: str,
) -> dict[str, str]:
    return {
        "project": project,
        "developer": developer,
        "contractor": contractor,
        "location": location,
        "region": region,
        "source_level": source_level,
        "source_name": source_name,
        "query": query,
        "search_url": google_url(query),
        "purpose": purpose,
        "priority": priority,
        "checked": "no",
        "result_status": "",
        "result_url": "",
        "notes": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def project_aliases(project: str, developer: str) -> list[str]:
    aliases = [project]

    p = project.lower()

    if "data4" in p or "data 4" in p:
        aliases += [
            "DATA4 Cornaredo",
            "DATA 4 MILAN",
            "D4 Data Center MIL1",
            "DATA4 campus Cornaredo",
        ]

    if "cyrus" in p:
        aliases += [
            "CyrusOne MIL1",
            "CyrusOne Italy I",
            "CyrusOne Segrate",
            "data center ex CISE Segrate",
        ]

    if "retelit" in p or "avalon" in p:
        aliases += [
            "Retelit Avalon 3",
            "Avalon 3",
            "Retelit data center",
            "Avalon Campus",
        ]

    if p == "rom1" or "rom1" in p:
        aliases += [
            "ROM1 data center",
            "Roma data center ROM1",
            "Rome data center ROM1",
        ]

    if developer:
        aliases.append(developer)

    # dedupe
    out = []
    seen = set()
    for a in aliases:
        a = norm_space(a)
        if not a:
            continue
        k = a.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(a)

    return out


def local_source_rows(row: dict[str, str]) -> list[dict[str, str]]:
    project = clean(row.get("project"))
    developer = clean(row.get("developer"))
    contractor = clean(row.get("contractor"))
    location = clean(row.get("location"))
    region = clean(row.get("region"))
    priority = clean(row.get("priority")) or "P2"

    if not project:
        return []

    aliases = project_aliases(project, developer)
    rows = []

    # Località override: alcuni progetti hanno iter su comuni/ambiti diversi dalla località sintetica dashboard.
    key = project.lower().strip()
    locations = LOCATION_OVERRIDES.get(key)

    if not locations:
        locations = [x.strip() for x in re.split(r"/|,|;", location) if x.strip()]

    if not locations and location:
        locations = [location]

    if not locations:
        locations = [""]

    for alias in aliases:
        for loc in locations:
            loc_part = f" {loc}" if loc else ""

            rows += [
                make_row(
                    project, developer, contractor, location, region,
                    "region",
                    f"Regione {region}" if region else "Regione",
                    f'"{alias}"{loc_part} VIA OR PAUR OR "verifica di assoggettabilità" OR "valutazione impatto ambientale"',
                    "Cercare procedimenti regionali VIA/PAUR/verifica assoggettabilità.",
                    priority,
                ),
                make_row(
                    project, developer, contractor, location, region,
                    "province/metropolitan_city",
                    "Provincia / Città Metropolitana",
                    f'"{alias}"{loc_part} "Città Metropolitana" OR Provincia emissioni atmosfera scarichi rumore',
                    "Cercare pareri ambientali, emissioni, scarichi, rumore, viabilità.",
                    priority,
                ),
                make_row(
                    project, developer, contractor, location, region,
                    "municipality",
                    f"Comune {loc}" if loc else "Comune",
                    f'"{alias}" "{loc}" "permesso di costruire" OR "conferenza dei servizi" OR "albo pretorio"',
                    "Cercare permessi, conferenze servizi, delibere, convenzioni urbanistiche.",
                    priority,
                ),
                make_row(
                    project, developer, contractor, location, region,
                    "suap",
                    "SUAP / Impresainungiorno",
                    f'"{alias}" "{loc}" SUAP "data center" "gruppi elettrogeni"',
                    "Cercare pratiche SUAP e atti edilizi/produttivi.",
                    priority,
                ),
                make_row(
                    project, developer, contractor, location, region,
                    "technical",
                    "Iter tecnico locale",
                    f'"{alias}" "{loc}" "gruppi elettrogeni" "cabina" "cavidotto" "Terna" "Enel"',
                    "Cercare connessioni elettriche, cabine, cavidotti, generatori.",
                    priority,
                ),
                make_row(
                    project, developer, contractor, location, region,
                    "commercial",
                    "Developer / contractor / press",
                    f'"{alias}" "{developer}" "{contractor}" "data center" MW contractor construction',
                    "Cercare fonti commerciali per MW IT, contractor, stato lavori.",
                    priority,
                ),
            ]

    return rows


def query_rank(row: dict[str, str]) -> int:
    project = row.get("project", "").lower()
    level = row.get("source_level", "").lower()
    query = row.get("query", "").lower()

    score = 100

    # P1 prima
    if row.get("priority") == "P1":
        score -= 30

    # Fonti più utili
    if level == "municipality":
        score -= 25
    elif level == "region":
        score -= 20
    elif level == "technical":
        score -= 18
    elif level == "commercial":
        score -= 15
    elif level == "province/metropolitan_city":
        score -= 12
    elif level == "suap":
        score -= 10

    # Query con parole forti
    strong_terms = [
        "permesso di costruire",
        "conferenza dei servizi",
        "gruppi elettrogeni",
        "cavidotto",
        "terna",
        "enel",
        "paur",
        "verifica di assoggettabilità",
        "valutazione impatto ambientale",
    ]

    for term in strong_terms:
        if term in query:
            score -= 3

    # Penalizza alias troppo generici
    generic = [
        '"retelit"',
        '"digital realty"',
        '"data4"',
        '"cyrusone"',
    ]

    if any(g in query for g in generic):
        score += 10

    return score


def write_top_queries(rows: list[dict[str, str]]) -> None:
    selected = []

    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["project"], []).append(row)

    for project, items in grouped.items():
        ranked = sorted(items, key=query_rank)
        for i, row in enumerate(ranked[:12], start=1):
            out = dict(row)
            out["rank"] = str(i)
            selected.append(out)

    fieldnames = [
        "rank",
        "project",
        "developer",
        "contractor",
        "location",
        "region",
        "source_level",
        "source_name",
        "query",
        "search_url",
        "purpose",
        "priority",
        "checked",
        "result_status",
        "result_url",
        "notes",
        "created_at",
    ]

    with TOP_OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)

    print(f"[OK] Written {TOP_OUTPUT} with {len(selected)} priority queries")


def main() -> None:
    matrix = read_csv(INPUT)

    candidates = [
        r for r in matrix
        if clean(r.get("next_enrichment_source")) == "Local authorities / commercial sources"
    ]

    rows = []
    for r in candidates:
        rows.extend(local_source_rows(r))

    # Filtro anti-rumore: CyrusOne MIL1 è a Segrate.
    # Milano resta utile per cavidotto/Terna/Lambrate/Città Metropolitana,
    # ma non per Comune/SUAP/permesso di costruire del data center.
    filtered_rows = []
    for r in rows:
        if (
            r.get("project") == "CyrusOne MIL1"
            and r.get("source_level") in {"municipality", "suap"}
            and '"Milano"' in r.get("query", "")
        ):
            continue
        filtered_rows.append(r)

    rows = filtered_rows

    # dedupe query
    deduped = []
    seen = set()
    for r in rows:
        key = (r["project"].lower(), r["query"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "project",
        "developer",
        "contractor",
        "location",
        "region",
        "source_level",
        "source_name",
        "query",
        "search_url",
        "purpose",
        "priority",
        "checked",
        "result_status",
        "result_url",
        "notes",
        "created_at",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"[OK] Written {OUTPUT} with {len(deduped)} source queries")
    write_top_queries(deduped)


if __name__ == "__main__":
    main()
