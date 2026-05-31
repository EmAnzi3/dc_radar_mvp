from pathlib import Path
from datetime import datetime
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


def split_terms(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


def quote(value: str) -> str:
    value = str(value or "").strip()
    if " " in value:
        return f'"{value}"'
    return value


def domain_from_url(url: str) -> str:
    return (
        str(url or "")
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )


def build_queries(row: dict) -> list[dict]:
    authority = row.get("authority", "")
    authority_type = row.get("authority_type", "")
    city = row.get("city", "")
    province = row.get("province", "")
    region = row.get("region", "")
    priority = row.get("priority", "")
    base_url = row.get("base_url", "")
    notes = row.get("notes", "")
    domain = domain_from_url(base_url)
    terms = split_terms(row.get("search_terms", ""))

    rows = []

    for term in terms:
        if domain:
            rows.append({
                "authority": authority,
                "authority_type": authority_type,
                "city": city,
                "province": province,
                "region": region,
                "priority": priority,
                "query_type": "authority_site_term",
                "query": f"site:{domain} {quote(term)}",
                "notes": notes,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    combos = [
        f'"{city}" "data center" "permesso di costruire"',
        f'"{city}" "data center" "conferenza dei servizi"',
        f'"{city}" "data center" SUAP',
        f'"{city}" datacenter "permesso di costruire"',
        f'"{city}" "variante urbanistica" "data center"',
        f'"{city}" "piano attuativo" "data center"',
        f'"{city}" "albo pretorio" "data center"',
        f'"{city}" "determinazione" "data center"',
        f'"{city}" "delibera" "data center"',
    ]

    for query in combos:
        rows.append({
            "authority": authority,
            "authority_type": authority_type,
            "city": city,
            "province": province,
            "region": region,
            "priority": priority,
            "query_type": "web_local_authority_combo",
            "query": query,
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    return rows


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = INPUT_DIR / "local_authority_watchlist.csv"

    if not source.exists() or source.stat().st_size == 0:
        print("Nessun local_authority_watchlist.csv trovato")
        return

    watchlist = pd.read_csv(source).fillna("")

    query_rows = []

    for _, row in watchlist.iterrows():
        query_rows.extend(build_queries(row.to_dict()))

    queries_out = OUTPUT_DIR / "local_authority_intelligence_queries.csv"

    if query_rows:
        df = pd.DataFrame(query_rows).drop_duplicates(
            subset=["authority", "query"]
        )
    else:
        df = pd.DataFrame()

    df.to_csv(queries_out, index=False, encoding="utf-8-sig")

    print(f"Creato {queries_out} ({len(df)} query)")


if __name__ == "__main__":
    run()
