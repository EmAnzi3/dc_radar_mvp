from pathlib import Path
from datetime import datetime
import pandas as pd


OUTPUT_DIR = Path("data/output")


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except Exception:
        return pd.DataFrame()


def to_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def run():
    source = OUTPUT_DIR / "italy_project_summary.csv"

    if not source.exists() or source.stat().st_size == 0:
        print("Nessun italy_project_summary.csv trovato")
        return

    df = read_csv_safe(source)

    if df.empty:
        print("italy_project_summary.csv vuoto")
        return

    df["mw_num"] = df["it_power_mw"].apply(to_float)

    dev_df = df.copy()
    dev_df["developer"] = dev_df["developer"].replace("", "Da identificare")

    developer = (
        dev_df.groupby("developer", dropna=False)
        .agg(
            projects_count=("project", "nunique"),
            known_mw_projects=("mw_num", lambda x: (x > 0).sum()),
            total_it_power_mw=("mw_num", "sum"),
            contractors=("contractor", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v))))),
            provinces=("province", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v))))),
            projects=("project", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v))))),
        )
        .reset_index()
    )

    developer["ranking_score"] = (
        developer["projects_count"] * 10
        + developer["known_mw_projects"] * 8
        + developer["total_it_power_mw"]
    )

    developer["checked_at"] = datetime.now().isoformat(timespec="seconds")
    developer = developer.sort_values(
        by=["ranking_score", "total_it_power_mw", "projects_count"],
        ascending=[False, False, False],
    )

    contractor = (
        df.groupby("contractor", dropna=False)
        .agg(
            projects_count=("project", "nunique"),
            developers_count=("developer", "nunique"),
            known_mw_projects=("mw_num", lambda x: (x > 0).sum()),
            total_it_power_mw=("mw_num", "sum"),
            developers=("developer", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v))))),
            provinces=("province", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v))))),
            projects=("project", lambda x: "; ".join(sorted(set(str(v) for v in x if str(v))))),
        )
        .reset_index()
    )

    contractor["ranking_score"] = (
        contractor["projects_count"] * 10
        + contractor["developers_count"] * 8
        + contractor["known_mw_projects"] * 8
        + contractor["total_it_power_mw"]
    )

    contractor["checked_at"] = datetime.now().isoformat(timespec="seconds")
    contractor = contractor.sort_values(
        by=["ranking_score", "total_it_power_mw", "projects_count"],
        ascending=[False, False, False],
    )

    dev_out = OUTPUT_DIR / "italy_developer_ranking.csv"
    contractor_out = OUTPUT_DIR / "italy_contractor_ranking.csv"

    developer.to_csv(dev_out, index=False, encoding="utf-8-sig")
    contractor.to_csv(contractor_out, index=False, encoding="utf-8-sig")

    print(f"Creato {dev_out} ({len(developer)} righe)")
    print(f"Creato {contractor_out} ({len(contractor)} righe)")


if __name__ == "__main__":
    run()
