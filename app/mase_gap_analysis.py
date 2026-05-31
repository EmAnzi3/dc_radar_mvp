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


def is_missing(value):
    value = clean(value)
    return value == "" or value.lower() in ["da identificare", "nan", "none", "0"]


def has_mase_evidence(project, city, mase_hits):
    if mase_hits.empty:
        return False

    blob = " ".join([
        " ".join(mase_hits.get(col, pd.Series(dtype=str)).astype(str).tolist())
        for col in mase_hits.columns
    ]).lower()

    project = clean(project).lower()
    city = clean(city).lower()

    return (project and project in blob) or (city and city in blob)


def add_gap(rows, project, city, province, developer, contractor, issue, severity, suggested_action, source_url=""):
    rows.append({
        "project": clean(project),
        "city": clean(city),
        "province": clean(province),
        "developer": clean(developer),
        "contractor": clean(contractor),
        "issue": issue,
        "severity": severity,
        "suggested_action": suggested_action,
        "source_url": clean(source_url),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })


def run():
    summary = read_csv_safe(OUTPUT_DIR / "italy_project_summary.csv")
    mase_hits = read_csv_safe(OUTPUT_DIR / "mase_entity_hits.csv")
    mase_docs = read_csv_safe(OUTPUT_DIR / "mase_document_files.csv")

    rows = []

    if summary.empty:
        print("Nessun italy_project_summary.csv trovato")
        return

    for _, r in summary.iterrows():
        project = clean(r.get("project", ""))
        city = clean(r.get("city", ""))
        province = clean(r.get("province", ""))
        developer = clean(r.get("developer", ""))
        contractor = clean(r.get("contractor", ""))
        mw = clean(r.get("it_power_mw", ""))
        source_url = clean(r.get("source_url", ""))

        if is_missing(developer):
            add_gap(
                rows,
                project,
                city,
                province,
                developer,
                contractor,
                "Developer/proponente mancante",
                "high",
                "Cercare fascicolo MASE/Regione/SUAP e aggiungere override verificato",
                source_url,
            )

        if is_missing(mw):
            add_gap(
                rows,
                project,
                city,
                province,
                developer,
                contractor,
                "MW IT non disponibile",
                "medium",
                "Verificare schede progetto, VIA/AIA, relazione tecnica o comunicati developer",
                source_url,
            )

        if is_missing(province):
            add_gap(
                rows,
                project,
                city,
                province,
                developer,
                contractor,
                "Provincia mancante",
                "low",
                "Aggiungere city_province_overrides.csv",
                source_url,
            )

        if "mite.gov.it" not in source_url.lower() and "mase" not in source_url.lower():
            if not has_mase_evidence(project, city, mase_hits) and not has_mase_evidence(project, city, mase_docs):
                add_gap(
                    rows,
                    project,
                    city,
                    province,
                    developer,
                    contractor,
                    "Evidenza MASE non collegata",
                    "medium",
                    "Verificare se esiste oggetto MASE collegato al progetto",
                    source_url,
                )

    out = OUTPUT_DIR / "mase_gaps.csv"

    if rows:
        df = pd.DataFrame(rows)
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        df["_rank"] = df["severity"].map(severity_rank).fillna(9)
        df = df.sort_values(by=["_rank", "project", "issue"])
        df = df.drop(columns=["_rank"])
    else:
        df = pd.DataFrame(columns=[
            "project", "city", "province", "developer", "contractor",
            "issue", "severity", "suggested_action", "source_url", "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} gap)")


if __name__ == "__main__":
    run()
