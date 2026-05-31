from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path


PROJECTS = Path("data/output/italy_project_summary.csv")
MASE_MATCHES = Path("data/output/mase_project_matches.csv")
MASE_TARGETS = Path("data/input/mase_targets.csv")
MASE_FACTS = Path("data/output/mase_project_facts_dashboard.csv")
OUTPUT = Path("data/output/dc_enrichment_matrix.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean(value: object) -> str:
    return str(value or "").strip()


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def row_blob(row: dict[str, str]) -> str:
    return " ".join(clean(v) for v in row.values())


def first(row: dict[str, str], names: list[str]) -> str:
    lookup = {k.lower(): k for k in row.keys()}

    for name in names:
        k = lookup.get(name.lower())
        if k:
            v = clean(row.get(k))
            if v:
                return v

    return ""


def extract_mase_id_from_text(text: str) -> str:
    text = clean(text)

    patterns = [
        r"/Info/(\d+)",
        r"Oggetti/Info/(\d+)",
        r"mase_object_id[^\d]{0,10}(\d+)",
        r"object_id[^\d]{0,10}(\d+)",
        r"\bID[_\s-]*VIP[^\d]{0,10}(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1)

    return ""


def extract_mase_id(row: dict[str, str]) -> str:
    direct = first(row, ["mase_object_id", "object_id", "id_vip", "idvip"])
    if direct and re.fullmatch(r"\d+", direct):
        return direct

    return extract_mase_id_from_text(row_blob(row))


def match_score(project: str, candidate: str) -> int:
    p = set(norm(project).split())
    c = set(norm(candidate).split())

    if not p or not c:
        return 0

    score = len(p & c) * 10

    if norm(project) and norm(project) in norm(candidate):
        score += 50

    if norm(candidate) and norm(candidate) in norm(project):
        score += 50

    return score


def best_match(project: str, rows: list[dict[str, str]], name_fields: list[str]) -> dict[str, str] | None:
    best = None
    best_score = 0

    for row in rows:
        names = [first(row, name_fields), row_blob(row)]
        score = max(match_score(project, n) for n in names if n)

        if score > best_score:
            best = row
            best_score = score

    if best_score >= 20:
        return best

    return None


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def same_number(a: str, b: str) -> bool:
    if not a or not b:
        return False

    def parse(x: str) -> float | None:
        m = re.search(r"\d+(?:[.,]\d+)?", str(x))
        if not m:
            return None
        return float(m.group(0).replace(",", "."))

    aa = parse(a)
    bb = parse(b)

    if aa is None or bb is None:
        return False

    return abs(aa - bb) < 0.01


def detect_next_source(
    mase_id: str,
    has_target: bool,
    has_facts: bool,
    has_proponent: bool,
    has_it: bool,
    has_mwt: bool,
    has_contractor: bool,
) -> tuple[str, str, str]:
    if not mase_id:
        return (
            "Local authorities / commercial sources",
            "MASE object not found in current targets/matches. Use Regione, Provincia/Città Metropolitana, Comune/SUAP, conferenza servizi, PAUR/VIA and commercial/developer sources.",
            "P1",
        )

    if not has_target:
        return (
            "MASE target",
            "Add MASE object to data/input/mase_targets.csv and run Stage 1/2.",
            "P1",
        )

    if not has_facts:
        return (
            "MASE PDF extraction",
            "Download/read MASE documents and generate facts for this object.",
            "P1",
        )

    missing = []
    if not has_proponent:
        missing.append("proponente")
    if not has_it:
        missing.append("MW IT")
    if not has_mwt:
        missing.append("MWt")
    if not has_contractor:
        missing.append("contractor")

    if missing:
        return (
            "Local authorities / commercial sources",
            "Complete missing fields: " + ", ".join(missing) + ". Use Regione, Provincia/Città Metropolitana, Comune/SUAP, conferenza servizi, PAUR/VIA.",
            "P2",
        )

    return (
        "Monitoring",
        "Record structurally enriched. Keep monitoring MASE and local acts for updates.",
        "P3",
    )


def main() -> None:
    projects = read_csv(PROJECTS)
    matches = read_csv(MASE_MATCHES)
    targets = read_csv(MASE_TARGETS)
    facts = read_csv(MASE_FACTS)

    targets_by_id = {extract_mase_id(r): r for r in targets if extract_mase_id(r)}
    facts_by_id = {extract_mase_id(r): r for r in facts if extract_mase_id(r)}

    rows = []

    for project_row in projects:
        project = first(project_row, ["project", "name", "title", "display_project"])
        developer = first(project_row, ["developer", "developer_hint", "primary_developer"])
        contractor = first(project_row, ["contractor", "gc", "general_contractor"])
        location = first(project_row, ["location", "municipality", "city", "comune"])
        region = first(project_row, ["region", "regione"])
        status = first(project_row, ["status", "stage"])
        dashboard_it = first(project_row, ["it_power_mw", "mw_it", "primary_it_power_mw"])
        dashboard_source_type = first(project_row, ["source_type", "source", "dashboard_source"])
        dashboard_source_url = first(project_row, ["source_url", "url"])

        mase_id = extract_mase_id(project_row)

        matched_row = None
        if not mase_id:
            matched_row = best_match(
                project,
                matches,
                ["project", "project_name", "name", "title", "display_project", "matched_project"],
            )
            if matched_row:
                mase_id = extract_mase_id(matched_row)

        target_row = targets_by_id.get(mase_id, {})
        fact_row = facts_by_id.get(mase_id, {})

        if not fact_row and project:
            fact_row = best_match(
                project,
                facts,
                ["display_project", "source_project", "project"],
            ) or {}

        if fact_row and not mase_id:
            mase_id = extract_mase_id(fact_row)

        has_target = bool(targets_by_id.get(mase_id))
        has_facts = bool(fact_row)

        mase_project = first(fact_row, ["display_project", "project"])
        mase_proponent = first(fact_row, ["primary_proponent"])
        mase_developer = first(fact_row, ["primary_developer", "developer_hint"])
        mase_campus = first(fact_row, ["campus_codes"])
        mase_it = first(fact_row, ["primary_it_power_mw"])
        mase_it_source = first(fact_row, ["primary_it_power_mw_source"])
        mase_mwt = first(fact_row, ["primary_thermal_power_mwt"])
        mase_site_area = first(fact_row, ["primary_site_area_m2"])
        mase_quality = first(fact_row, ["quality_status"])
        mase_notes = first(fact_row, ["notes"])

        alignment_issue = ""

        if dashboard_it and not mase_it:
            alignment_issue = "Dashboard has MW IT but MASE facts empty"
        elif dashboard_it and mase_it and not same_number(dashboard_it, mase_it):
            alignment_issue = f"Dashboard MW IT ({dashboard_it}) differs from MASE facts ({mase_it})"
        elif mase_it and mase_it_source and mase_it_source.upper() != "MASE PDF":
            alignment_issue = f"MW IT in MASE facts comes from non-MASE source: {mase_it_source}"

        next_source, next_action, priority = detect_next_source(
            mase_id=mase_id,
            has_target=has_target,
            has_facts=has_facts,
            has_proponent=bool(mase_proponent),
            has_it=bool(mase_it or dashboard_it),
            has_mwt=bool(mase_mwt),
            has_contractor=bool(contractor),
        )

        rows.append({
            "project": project,
            "developer": developer,
            "contractor": contractor,
            "location": location,
            "region": region,
            "status": status,
            "dashboard_it_power_mw": dashboard_it,
            "dashboard_source_type": dashboard_source_type,
            "dashboard_source_url": dashboard_source_url,
            "mase_object_id": mase_id,
            "mase_target": yes_no(has_target),
            "mase_facts": yes_no(has_facts),
            "mase_project": mase_project,
            "mase_developer": mase_developer,
            "mase_primary_proponent": mase_proponent,
            "mase_campus_codes": mase_campus,
            "mase_it_power_mw": mase_it,
            "mase_it_power_mw_source": mase_it_source,
            "mase_thermal_power_mwt": mase_mwt,
            "mase_site_area_m2": mase_site_area,
            "mase_quality_status": mase_quality,
            "alignment_issue": alignment_issue,
            "next_enrichment_source": next_source,
            "next_action": next_action,
            "priority": priority,
            "mase_notes": mase_notes,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    deduped_rows = []
    seen_keys = set()

    for row in rows:
        key = (
            row.get("project", "").strip().lower(),
            row.get("developer", "").strip().lower(),
            row.get("location", "").strip().lower(),
            row.get("mase_object_id", "").strip(),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_rows.append(row)

    rows = deduped_rows

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "project",
        "developer",
        "contractor",
        "location",
        "region",
        "status",
        "dashboard_it_power_mw",
        "dashboard_source_type",
        "dashboard_source_url",
        "mase_object_id",
        "mase_target",
        "mase_facts",
        "mase_project",
        "mase_developer",
        "mase_primary_proponent",
        "mase_campus_codes",
        "mase_it_power_mw",
        "mase_it_power_mw_source",
        "mase_thermal_power_mwt",
        "mase_site_area_m2",
        "mase_quality_status",
        "alignment_issue",
        "next_enrichment_source",
        "next_action",
        "priority",
        "mase_notes",
        "checked_at",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Written {OUTPUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
