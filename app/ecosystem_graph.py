from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")
INPUT_DIR = Path("data/input")


ITALY_COUNTRY_VALUES = {"", "italy", "italia"}


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


def load_aliases() -> dict:
    aliases_file = INPUT_DIR / "company_aliases.csv"
    df = read_csv_safe(aliases_file)

    aliases = {}

    if df.empty:
        return aliases

    for _, row in df.iterrows():
        alias = clean_text(row.get("alias", ""))
        canonical = clean_text(row.get("canonical_name", ""))

        if alias and canonical:
            aliases[alias.lower()] = canonical

    return aliases


ALIASES = load_aliases()


def normalize_company(value: str) -> str:
    value = clean_text(value)

    if not value:
        return ""

    low = value.lower()

    if low in ALIASES:
        return ALIASES[low]

    for alias, canonical in ALIASES.items():
        if alias in low:
            return canonical

    return value


def is_italian_row(row) -> bool:
    country = clean_text(row.get("country", "")).lower()
    province = clean_text(row.get("province", ""))
    city = clean_text(row.get("city", ""))

    if country in ITALY_COUNTRY_VALUES:
        return True

    if province:
        return True

    italian_city_hints = [
        "Roma",
        "Milano",
        "Settimo Milanese",
        "Cornaredo",
        "Vittuone",
        "Segrate",
        "Bornasco",
        "Lacchiarella",
        "Pomezia",
    ]

    return city in italian_city_hints


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


def build_from_mercury_italy_only(rows):
    # Mercury estero resta benchmark separato in mercury_projects.csv.
    # Qui entra solo se country/province/city indicano chiaramente Italia.
    df = read_csv_safe(OUTPUT_DIR / "mercury_projects.csv")

    if df.empty:
        return

    for _, row in df.iterrows():
        if not is_italian_row(row):
            continue

        developer = clean_text(row.get("developer", ""))
        contractor = clean_text(row.get("contractor", ""))
        project = clean_text(row.get("project", ""))
        city = clean_text(row.get("city", ""))
        country = clean_text(row.get("country", ""))
        location = " ".join(x for x in [city, country] if x)
        package = clean_text(row.get("work_scope", ""))
        confidence = row.get("confidence", 0)
        evidence = clean_text(row.get("evidence", ""))
        source_url = clean_text(row.get("source_url", ""))

        if developer and developer.lower() != "confidential":
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
    build_from_mercury_italy_only(rows)
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
