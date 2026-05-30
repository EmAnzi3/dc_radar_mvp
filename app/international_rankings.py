from pathlib import Path
from datetime import datetime
import pandas as pd


OUTPUT_DIR = Path("data/output")


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def clean_value(value):
    if pd.isna(value):
        return 0
    try:
        return float(value)
    except Exception:
        return 0


def run():
    source = OUTPUT_DIR / "international_developer_watchlist.csv"

    if not source.exists() or source.stat().st_size == 0:
        print("Nessun international_developer_watchlist.csv trovato")
        return

    df = pd.read_csv(source)

    if df.empty:
        print("international_developer_watchlist.csv vuoto")
        return

    df["contract_value_eur_num"] = df["contract_value_eur"].apply(clean_value)

    developer = (
        df.groupby(["developer", "parent_company", "entity_type"], dropna=False)
        .agg(
            projects_count=("project", "nunique"),
            countries_count=("country", "nunique"),
            total_contract_value_eur=("contract_value_eur_num", "sum"),
            avg_contract_value_eur=("contract_value_eur_num", "mean"),
            known_value_projects=("contract_value_eur_num", lambda x: (x > 0).sum()),
            contractors=("contractor", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v) != "nan")))),
            countries=("country", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v) and str(v) != "nan")))),
            projects=("project", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v) and str(v) != "nan")))),
        )
        .reset_index()
    )

    developer["ranking_score"] = (
        developer["projects_count"] * 10
        + developer["countries_count"] * 5
        + developer["known_value_projects"] * 10
        + developer["total_contract_value_eur"] / 10_000_000
    )

    developer["checked_at"] = datetime.now().isoformat(timespec="seconds")

    developer = developer.sort_values(
        by=["ranking_score", "total_contract_value_eur", "projects_count"],
        ascending=[False, False, False],
    )

    developer_out = OUTPUT_DIR / "international_developer_ranking.csv"
    developer.to_csv(developer_out, index=False, encoding="utf-8-sig")

    contractor = (
        df.groupby(["contractor"], dropna=False)
        .agg(
            projects_count=("project", "nunique"),
            developers_count=("developer", "nunique"),
            countries_count=("country", "nunique"),
            total_contract_value_eur=("contract_value_eur_num", "sum"),
            avg_contract_value_eur=("contract_value_eur_num", "mean"),
            known_value_projects=("contract_value_eur_num", lambda x: (x > 0).sum()),
            developers=("developer", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v) and str(v) != "nan")))),
            countries=("country", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v) and str(v) != "nan")))),
            projects=("project", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v) and str(v) != "nan")))),
        )
        .reset_index()
    )

    contractor["ranking_score"] = (
        contractor["projects_count"] * 10
        + contractor["developers_count"] * 8
        + contractor["countries_count"] * 5
        + contractor["known_value_projects"] * 10
        + contractor["total_contract_value_eur"] / 10_000_000
    )

    contractor["checked_at"] = datetime.now().isoformat(timespec="seconds")

    contractor = contractor.sort_values(
        by=["ranking_score", "total_contract_value_eur", "projects_count"],
        ascending=[False, False, False],
    )

    contractor_out = OUTPUT_DIR / "international_contractor_ranking.csv"
    contractor.to_csv(contractor_out, index=False, encoding="utf-8-sig")

    print(f"Creato {developer_out} ({len(developer)} righe)")
    print(f"Creato {contractor_out} ({len(contractor)} righe)")


if __name__ == "__main__":
    run()
