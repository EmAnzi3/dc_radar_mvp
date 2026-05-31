from pathlib import Path
from datetime import datetime
import pandas as pd
import re


OUTPUT_DIR = Path("data/output")


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except Exception:
        return pd.DataFrame()


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_project_name(value):
    value = clean(value)

    replacements = {
        "Digital Realty ROM1": "ROM1",
    }

    return replacements.get(value, value)


def add_row(rows, project, city, province, developer, contractor, mw_it, status, source_type, source_url, confidence):
    if not clean(project):
        return

    rows.append({
        "project": normalize_project_name(project),
        "city": clean(city),
        "province": clean(province),
        "developer": clean(developer) or "Da identificare",
        "contractor": clean(contractor) or "Da identificare",
        "it_power_mw": mw_it,
        "status": clean(status) or "Da verificare",
        "source_type": clean(source_type),
        "source_url": clean(source_url),
        "confidence": confidence,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })


def run():
    rows = []

    developer_master = read_csv_safe(OUTPUT_DIR / "developer_master.csv")
    manual_leads = read_csv_safe(OUTPUT_DIR / "manual_contractor_leads.csv")

    if not developer_master.empty:
        for _, r in developer_master.iterrows():
            add_row(
                rows,
                project=r.get("project", ""),
                city=r.get("city", ""),
                province=r.get("province", ""),
                developer=r.get("developer", ""),
                contractor=r.get("contractor", ""),
                mw_it=r.get("it_power_mw", ""),
                status=r.get("status", ""),
                source_type="Developer Master",
                source_url=r.get("source_url", ""),
                confidence=r.get("confidence", ""),
            )

    if not manual_leads.empty:
        for _, r in manual_leads.iterrows():
            add_row(
                rows,
                project=r.get("project", ""),
                city=r.get("location", ""),
                province="",
                developer=r.get("developer", ""),
                contractor=r.get("company", ""),
                mw_it="",
                status="Da verificare",
                source_type="Manual lead",
                source_url=r.get("source_url", ""),
                confidence=r.get("confidence", ""),
            )

    out = OUTPUT_DIR / "italy_project_summary.csv"

    if rows:
        df = pd.DataFrame(rows)
        df["_has_province"] = df["province"].apply(lambda x: 1 if str(x).strip() else 0)
        df["_has_mw"] = df["it_power_mw"].apply(lambda x: 1 if str(x).strip() else 0)
        df["_confidence_num"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0)

        df = df.sort_values(
            by=["project", "developer", "contractor", "_has_province", "_has_mw", "_confidence_num"],
            ascending=[True, True, True, False, False, False],
        )

        df = df.drop_duplicates(
            subset=["project", "developer", "contractor"],
            keep="first",
        )

        df = df.drop(columns=["_has_province", "_has_mw", "_confidence_num"])
        df = df.sort_values(by=["province", "city", "project"], ascending=[True, True, True])
    else:
        df = pd.DataFrame(columns=[
            "project", "city", "province", "developer", "contractor",
            "it_power_mw", "status", "source_type", "source_url",
            "confidence", "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()


