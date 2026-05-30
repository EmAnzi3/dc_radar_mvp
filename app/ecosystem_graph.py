from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")


def clean_text(value) -> str:
    value = "" if pd.isna(value) else str(value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_company(value: str) -> str:
    value = clean_text(value)

    replacements = {
        "Vantage": "Vantage Data Centers",
        "Digital Realty": "Digital Realty",
        "Equinix": "Equinix",
        "DATA4": "DATA4",
        "Microsoft": "Microsoft",
        "CyrusOne": "CyrusOne",
        "Techbau": "Techbau",
        "DBA": "DBA Group",
        "DBA Group": "DBA Group",
        "Schneider": "Schneider Electric",
        "Schneider Electric": "Schneider Electric",
        "Generale Prefabbricati": "Generale Prefabbricati",
        "A2A": "A2A Calore",
        "A2A Calore": "A2A Calore",
    }

    for key, normalized in replacements.items():
        if key.lower() == value.lower():
            return normalized

    for key, normalized in replacements.items():
        if key.lower() in value.lower():
            return normalized

    return value


def add_edge(rows, source, relationship, target, project="", location="", package="", confidence=0, evidence="", source_url=""):
    source = normalize_company(source)
    target = normalize_company(target)

    if not source or not target:
        return

    if source == target:
        return

    rows.append({
        "source_company": source,
        "relationship": relationship,
        "target_company": target,
        "project": clean_text(project),
        "location": clean_text(location),
        "package": clean_text(package),
        "confidence": confidence,
        "evidence": clean_text(evidence)[:800],
        "source_url": clean_text(source_url),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def build_from_developer_master(rows):
    df = read_csv_safe(OUTPUT_DIR / "developer_master.csv")

    if df.empty:
        return

    for _, row in df.iterrows():
        developer = clean_text(row.get("developer", ""))
        contractor = clean_text(row.get("contractor", ""))
        project = clean_text(row.get("project", ""))
        city = clean_text(row.get("city", ""))
        province = clean_text(row.get("province", ""))
        location = " ".join(x for x in [city, province] if x)
        package = clean_text(row.get("work_scope", ""))
        source_url = clean_text(row.get("source_url", ""))
        confidence = row.get("confidence", 0)

        add_edge(
            rows,
            source=contractor,
            relationship="contractor_for",
            target=developer,
            project=project,
            location=location,
            package=package,
            confidence=confidence,
            evidence=f"{contractor} contractor for {developer} on {project}",
            source_url=source_url,
        )


def build_from_manual_leads(rows):
    df = read_csv_safe(OUTPUT_DIR / "manual_contractor_leads.csv")

    if df.empty:
        return

    for _, row in df.iterrows():
        developer = clean_text(row.get("developer", ""))
        company = clean_text(row.get("company", ""))
        project = clean_text(row.get("project", ""))
        location = clean_text(row.get("location", ""))
        role = clean_text(row.get("role", ""))
        package = clean_text(row.get("package", ""))
        confidence = row.get("confidence", 0)
        evidence = clean_text(row.get("evidence", ""))
        source_url = clean_text(row.get("source_url", ""))

        relationship = "contractor_for"

        low = f"{company} {role} {package}".lower()

        if "generale prefabbricati" in low or "structural" in low or "prefab" in low:
            relationship = "structural_for"
        elif "a2a" in low or "cooling" in low:
            relationship = "energy_cooling_for"
        elif "dba" in low or "engineering" in low:
            relationship = "engineering_for"
        else:
            relationship = "contractor_for"

        add_edge(
            rows,
            source=company,
            relationship=relationship,
            target=developer,
            project=project,
            location=location,
            package=package,
            confidence=confidence,
            evidence=evidence,
            source_url=source_url,
        )


def build_from_contractor_facts(rows):
    df = read_csv_safe(OUTPUT_DIR / "contractor_project_facts.csv")

    if df.empty:
        return

    for _, row in df.iterrows():
        developer = clean_text(row.get("developer", ""))
        contractor = clean_text(row.get("contractor", ""))
        project = clean_text(row.get("project", ""))
        city = clean_text(row.get("city", ""))
        province = clean_text(row.get("province", ""))
        location = " ".join(x for x in [city, province] if x)
        package = clean_text(row.get("work_scope", ""))
        confidence = row.get("confidence", 0)
        evidence = clean_text(row.get("evidence", ""))
        source_url = clean_text(row.get("source_url", ""))

        if developer:
            add_edge(
                rows,
                source=contractor,
                relationship="contractor_for",
                target=developer,
                project=project,
                location=location,
                package=package,
                confidence=confidence,
                evidence=evidence,
                source_url=source_url,
            )


def build_from_ida_watchlist(rows):
    df = read_csv_safe(OUTPUT_DIR / "ida_ecosystem_watchlist.csv")

    if df.empty:
        return

    for _, row in df.iterrows():
        company = clean_text(row.get("company", ""))
        category = clean_text(row.get("category", ""))
        confidence = row.get("confidence", 0)
        source_url = clean_text(row.get("base_url", ""))
        notes = clean_text(row.get("notes", ""))

        if company == "IDA Italian Datacenter Association":
            continue

        add_edge(
            rows,
            source=company,
            relationship=f"member_or_watchlist_{category}",
            target="Italian Datacenter Association",
            project="",
            location="",
            package=category,
            confidence=confidence,
            evidence=notes,
            source_url=source_url,
        )


def run():
    rows = []

    build_from_developer_master(rows)
    build_from_manual_leads(rows)
    build_from_contractor_facts(rows)
    build_from_ida_watchlist(rows)

    out = OUTPUT_DIR / "ecosystem_graph.csv"

    if rows:
        df = pd.DataFrame(rows)
        df = df.drop_duplicates(
            subset=[
                "source_company",
                "relationship",
                "target_company",
                "project",
                "source_url",
            ]
        )
        df = df.sort_values(
            by=["confidence", "source_company", "target_company"],
            ascending=[False, True, True],
        )
    else:
        df = pd.DataFrame(columns=[
            "source_company",
            "relationship",
            "target_company",
            "project",
            "location",
            "package",
            "confidence",
            "evidence",
            "source_url",
            "checked_at",
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} relazioni)")


if __name__ == "__main__":
    run()

