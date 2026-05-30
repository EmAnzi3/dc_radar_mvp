from pathlib import Path
from datetime import datetime
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


def split_terms(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


def quote(term: str) -> str:
    if " " in term:
        return f'"{term}"'
    return term


def domain_from_url(url: str) -> str:
    return (
        str(url or "")
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )


def build_queries(row: dict) -> list[dict]:
    company = row.get("company", "")
    category = row.get("category", "")
    priority = row.get("priority", "")
    base_url = row.get("base_url", "")
    notes = row.get("notes", "")
    terms = split_terms(row.get("search_terms", ""))

    domain = domain_from_url(base_url)
    rows = []

    if domain:
        for term in terms:
            rows.append({
                "company": company,
                "category": category,
                "priority": priority,
                "query_type": "company_site_ida_relation",
                "query": f"site:{domain} {quote(term)}",
                "notes": notes,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    rows.extend([
        {
            "company": company,
            "category": category,
            "priority": priority,
            "query_type": "ida_site_company",
            "query": f'site:italiandatacenter.com "{company}"',
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        },
        {
            "company": company,
            "category": category,
            "priority": priority,
            "query_type": "web_ida_company",
            "query": f'"{company}" "Italian Datacenter Association"',
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        },
        {
            "company": company,
            "category": category,
            "priority": priority,
            "query_type": "web_ida_data_center",
            "query": f'"{company}" IDA "data center" Italy',
            "notes": notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        },
    ])

    return rows


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = INPUT_DIR / "ida_watchlist.csv"

    if not source.exists() or source.stat().st_size == 0:
        print("Nessun ida_watchlist.csv trovato")
        return

    watchlist = pd.read_csv(source)

    query_rows = []
    classified_rows = []

    for _, row in watchlist.iterrows():
        data = row.to_dict()
        query_rows.extend(build_queries(data))

        classified_rows.append({
            "company": data.get("company", ""),
            "category": data.get("category", ""),
            "priority": data.get("priority", ""),
            "base_url": data.get("base_url", ""),
            "notes": data.get("notes", ""),
            "relationship_type": "IDA / data center ecosystem watchlist",
            "confidence": 40 if data.get("category") != "association" else 80,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    queries_out = OUTPUT_DIR / "ida_generated_queries.csv"
    classified_out = OUTPUT_DIR / "ida_ecosystem_watchlist.csv"

    pd.DataFrame(query_rows).drop_duplicates().to_csv(
        queries_out, index=False, encoding="utf-8-sig"
    )

    pd.DataFrame(classified_rows).drop_duplicates().to_csv(
        classified_out, index=False, encoding="utf-8-sig"
    )

    print(f"Creato {queries_out} ({len(query_rows)} query)")
    print(f"Creato {classified_out} ({len(classified_rows)} righe)")


if __name__ == "__main__":
    run()
