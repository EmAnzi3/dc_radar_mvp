from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")
INPUT_DIR = Path("data/input")


def clean_text(value) -> str:
    value = "" if pd.isna(value) else str(value)
    return re.sub(r"\s+", " ", value).strip()


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def load_aliases():
    aliases = {}
    df = read_csv_safe(INPUT_DIR / "company_aliases.csv")

    if df.empty:
        return aliases

    for _, row in df.iterrows():
        alias = clean_text(row.get("alias", ""))
        canonical = clean_text(row.get("canonical_name", ""))
        parent = clean_text(row.get("parent_company", ""))
        entity_type = clean_text(row.get("entity_type", ""))

        if alias:
            aliases[alias.lower()] = {
                "canonical_name": canonical or alias,
                "parent_company": parent or canonical or alias,
                "entity_type": entity_type,
            }

    return aliases


ALIASES = load_aliases()


def normalize_company(value: str) -> tuple[str, str, str]:
    value = clean_text(value)

    if not value:
        return "", "", ""

    low = value.lower()

    if low in ALIASES:
        item = ALIASES[low]
        return (
            item.get("canonical_name", value),
            item.get("parent_company", item.get("canonical_name", value)),
            item.get("entity_type", ""),
        )

    for alias, item in ALIASES.items():
        if alias in low:
            return (
                item.get("canonical_name", value),
                item.get("parent_company", item.get("canonical_name", value)),
                item.get("entity_type", ""),
            )

    return value, value, ""


def is_confidential(value: str) -> bool:
    return clean_text(value).lower() in ["confidential", "confidential client", ""]


def run():
    source = OUTPUT_DIR / "mercury_projects.csv"

    if not source.exists() or source.stat().st_size == 0:
        print("Nessun mercury_projects.csv trovato")
        return

    mercury = pd.read_csv(source)
    rows = []

    for _, row in mercury.iterrows():
        developer_raw = clean_text(row.get("developer", ""))

        if is_confidential(developer_raw):
            developer = "Confidential"
            parent = "Unknown"
            entity_type = "unknown"
        else:
            developer, parent, entity_type = normalize_company(developer_raw)

        rows.append({
            "developer": developer,
            "parent_company": parent,
            "entity_type": entity_type or "developer",
            "project": clean_text(row.get("project", "")),
            "contractor": clean_text(row.get("contractor", "")),
            "city": clean_text(row.get("city", "")),
            "country": clean_text(row.get("country", "")),
            "contract_value_eur": row.get("contract_value_eur", ""),
            "timeframe": clean_text(row.get("timeframe", "")),
            "work_scope": clean_text(row.get("work_scope", "")),
            "source_url": clean_text(row.get("source_url", "")),
            "confidence": row.get("confidence", ""),
            "watchlist_reason": "International benchmark from Mercury project portfolio",
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    out = OUTPUT_DIR / "international_developer_watchlist.csv"

    if rows:
        df = pd.DataFrame(rows)
        df = df.drop_duplicates(
            subset=["developer", "project", "contractor", "source_url"]
        )
        df = df.sort_values(
            by=["contract_value_eur", "developer", "project"],
            ascending=[False, True, True],
        )
    else:
        df = pd.DataFrame()

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()
