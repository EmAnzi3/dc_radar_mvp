from pathlib import Path
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


def split_terms(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


def quote(term: str) -> str:
    if " " in term:
        return f'"{term}"'
    return term


def generate_queries_for_source(row: dict) -> list[dict]:
    source_name = row.get("source_name", "")
    source_type = row.get("source_type", "")
    priority = row.get("priority", "")
    base_url = str(row.get("base_url", "") or "").strip()
    terms = split_terms(row.get("search_terms", ""))

    queries = []

    if not terms:
        return queries

    domain = (
        base_url
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )

    # Query singole mirate site:
    for term in terms:
        queries.append({
            "source_name": source_name,
            "source_type": source_type,
            "priority": priority,
            "query_type": "site_single_term",
            "query": f"site:{domain} {quote(term)}",
            "notes": row.get("notes", ""),
        })

    # Query combinate data center + termine
    for term in terms:
        if term.lower() in ["data center", "datacenter"]:
            continue
        queries.append({
            "source_name": source_name,
            "source_type": source_type,
            "priority": priority,
            "query_type": "site_datacenter_combo",
            "query": f'site:{domain} ("data center" OR datacenter) {quote(term)}',
            "notes": row.get("notes", ""),
        })

    # Query specifiche per enti locali
    if source_type in ["municipality", "region", "suap_sue", "public_portal"]:
        local_keywords = [
            "impresa",
            "impresa esecutrice",
            "direzione lavori",
            "permesso di costruire",
            "conferenza dei servizi",
            "piano attuativo",
            "variante urbanistica",
            "ordinanza",
            "albo pretorio",
        ]

        for kw in local_keywords:
            queries.append({
                "source_name": source_name,
                "source_type": source_type,
                "priority": priority,
                "query_type": "public_authority_gc_mining",
                "query": f'site:{domain} ("data center" OR datacenter) "{kw}"',
                "notes": row.get("notes", ""),
            })

    # Query specifiche contractor
    if source_type in ["contractor", "engineering"]:
        contractor_keywords = [
            "awarded",
            "selected",
            "general contractor",
            "EPC",
            "design and build",
            "construction",
            "MEP",
            "civil works",
        ]

        for kw in contractor_keywords:
            queries.append({
                "source_name": source_name,
                "source_type": source_type,
                "priority": priority,
                "query_type": "contractor_award_mining",
                "query": f'site:{domain} ("data center" OR datacenter OR "data centre") "{kw}" Italy',
                "notes": row.get("notes", ""),
            })

    return queries


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    watchlist_file = INPUT_DIR / "source_watchlist.csv"

    if not watchlist_file.exists() or watchlist_file.stat().st_size == 0:
        print("Nessuna source_watchlist trovata")
        return

    watchlist = pd.read_csv(watchlist_file)

    rows = []
    for _, row in watchlist.iterrows():
        rows.extend(generate_queries_for_source(row.to_dict()))

    out = OUTPUT_DIR / "generated_queries.csv"
    pd.DataFrame(rows).drop_duplicates().to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(rows)} query)")


if __name__ == "__main__":
    run()
