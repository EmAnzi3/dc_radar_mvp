from pathlib import Path
from datetime import datetime
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


LOCAL_AUTHORITY_KEYWORDS = [
    "data center",
    "datacenter",
    "centro elaborazione dati",
    "server farm",
    "permesso di costruire",
    "conferenza dei servizi",
    "piano attuativo",
    "variante urbanistica",
    "ordinanza",
    "albo pretorio",
    "impresa",
    "direzione lavori",
    "cantiere",
]


def build_local_queries(row: dict) -> list[dict]:
    source_name = row.get("source_name", "")
    source_type = row.get("source_type", "")
    base_url = str(row.get("base_url", "") or "").strip()
    priority = row.get("priority", "")

    if source_type not in ["municipality", "region", "suap_sue", "public_portal"]:
        return []

    domain = (
        base_url
        .replace("https://", "")
        .replace("http://", "")
        .split("/")[0]
    )

    rows = []

    for keyword in LOCAL_AUTHORITY_KEYWORDS:
        rows.append({
            "source_name": source_name,
            "source_type": source_type,
            "priority": priority,
            "query_type": "local_authority_site_search",
            "query": f'site:{domain} "{keyword}"',
            "target_domain": domain,
            "keyword": keyword,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    for keyword in [
        "data center impresa",
        "data center permesso di costruire",
        "data center conferenza dei servizi",
        "data center piano attuativo",
        "data center variante urbanistica",
        "data center direzione lavori",
        "data center cantiere",
    ]:
        rows.append({
            "source_name": source_name,
            "source_type": source_type,
            "priority": priority,
            "query_type": "local_authority_gc_combo",
            "query": f'site:{domain} "{keyword}"',
            "target_domain": domain,
            "keyword": keyword,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    return rows


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_file = INPUT_DIR / "source_watchlist.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessuna source_watchlist trovata")
        return

    watchlist = pd.read_csv(source_file)

    rows = []
    for _, row in watchlist.iterrows():
        rows.extend(build_local_queries(row.to_dict()))

    out = OUTPUT_DIR / "local_authority_queries.csv"
    pd.DataFrame(rows).drop_duplicates().to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(rows)} query)")


if __name__ == "__main__":
    run()
