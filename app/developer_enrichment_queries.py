from pathlib import Path
from datetime import datetime
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


CANDIDATE_DEVELOPERS = [
    "Vantage",
    "Vantage Data Centers",
    "Equinix",
    "Digital Realty",
    "DATA4",
    "CyrusOne",
    "Microsoft",
    "CloudHQ",
    "STACK Infrastructure",
    "Aruba",
]


def quote(value: str) -> str:
    value = str(value or "").strip()
    if " " in value:
        return f'"{value}"'
    return value


def build_queries(row: dict) -> list[dict]:
    project = str(row.get("project", "") or "").strip()
    city = str(row.get("city", "") or "").strip()
    province = str(row.get("province", "") or "").strip()
    contractor = str(row.get("known_contractor", "") or "").strip()
    mw = str(row.get("known_mw_it", "") or "").strip()
    priority = str(row.get("priority", "") or "").strip()
    notes = str(row.get("notes", "") or "").strip()

    rows = []

    base_queries = [
        f'"{project}" "{city}" "data center"',
        f'"{project}" "{city}" datacenter',
        f'"{project}" "{contractor}" "data center"',
        f'"{project}" "{contractor}" cliente',
        f'"{project}" "{contractor}" "client"',
        f'"{project}" "{mw} MW" "data center"',
        f'"{project}" "{province}" "data center"',
        f'"{city}" "{mw} MW" "data center"',
        f'"{city}" "{contractor}" "data center"',
        f'"{city}" "data center" "Techbau"',
    ]

    for query in base_queries:
        rows.append({
            "project": project,
            "city": city,
            "province": province,
            "known_contractor": contractor,
            "priority": priority,
            "query_type": "direct_project_enrichment",
            "query": query,
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    for developer in CANDIDATE_DEVELOPERS:
        rows.append({
            "project": project,
            "city": city,
            "province": province,
            "known_contractor": contractor,
            "priority": priority,
            "query_type": "candidate_developer_match",
            "query": f'"{project}" "{city}" "{developer}"',
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })
        rows.append({
            "project": project,
            "city": city,
            "province": province,
            "known_contractor": contractor,
            "priority": priority,
            "query_type": "candidate_developer_contractor_match",
            "query": f'"{project}" "{contractor}" "{developer}"',
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    local_authority_queries = [
        f'site:comune.settimomilanese.mi.it "{project}"',
        f'site:comune.settimomilanese.mi.it "data center"',
        f'site:comune.settimomilanese.mi.it "Techbau"',
        f'site:comune.settimomilanese.mi.it "Vantage"',
        f'site:comune.settimomilanese.mi.it "Equinix"',
        f'site:comune.settimomilanese.mi.it "conferenza dei servizi" "data center"',
        f'site:comune.settimomilanese.mi.it "permesso di costruire" "data center"',
        f'site:comune.settimomilanese.mi.it "piano attuativo" "data center"',
        f'site:comune.settimomilanese.mi.it "variante urbanistica" "data center"',
    ]

    for query in local_authority_queries:
        rows.append({
            "project": project,
            "city": city,
            "province": province,
            "known_contractor": contractor,
            "priority": priority,
            "query_type": "local_authority_enrichment",
            "query": query,
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    return rows


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = INPUT_DIR / "developer_enrichment_targets.csv"

    if not source.exists() or source.stat().st_size == 0:
        print("Nessun developer_enrichment_targets.csv trovato")
        return

    targets = pd.read_csv(source)

    rows = []

    for _, row in targets.iterrows():
        rows.extend(build_queries(row.to_dict()))

    out = OUTPUT_DIR / "developer_enrichment_queries.csv"

    if rows:
        df = pd.DataFrame(rows).drop_duplicates(subset=["project", "query"])
    else:
        df = pd.DataFrame()

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} query)")


if __name__ == "__main__":
    run()
