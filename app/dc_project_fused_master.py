from __future__ import annotations

import csv
import json
import re
from pathlib import Path


MASE_DASHBOARD = Path("data/output/mase_project_facts_dashboard.csv")
CONFIDENCE = Path("data/output/mase_facts_confidence_report.csv")
ACTION_QUEUE = Path("data/output/mase_facts_action_queue.csv")
TARGETS = Path("data/input/mase_targets.csv")
ENRICHMENT_MATRIX = Path("data/output/dc_enrichment_matrix.csv")
PUBLIC_LEADS = Path("data/output/combined_public_leads.csv")

OUTPUT = Path("data/output/dc_project_fused_master.csv")
JSON_OUTPUT = Path("data/output/dc_project_fused_master.json")


CANONICAL = {
    "Vantage MXP2": {
        "operator": "Vantage Data Centers",
        "aliases": ["Vantage MXP2", "Vantage", "MXP2", "MXP21", "MXP22"],
    },
    "Equinix ML9": {
        "operator": "Equinix",
        "aliases": ["Equinix ML9", "ML9"],
    },
    "Equinix ML7-ML8": {
        "operator": "Equinix",
        "aliases": ["Equinix ML7-ML8", "Equinix ML7 ML8", "ML7", "ML8"],
    },
    "Equinix ML10-ML11": {
        "operator": "Equinix",
        "aliases": ["Equinix ML10-ML11", "ML10", "ML11"],
    },
    "Equinix ML5-ML6": {
        "operator": "Equinix",
        "aliases": ["Equinix ML5-ML6", "ML5", "ML6"],
    },
    "Microsoft Bornasco": {
        "operator": "Microsoft",
        "aliases": ["Microsoft Bornasco", "Microsoft", "MIL05", "MIL06"],
    },
    "CyrusOne MIL1": {
        "operator": "CyrusOne",
        "aliases": ["CyrusOne MIL1", "MIL1", "CyrusOne"],
    },
    "DATA4 Cornaredo": {
        "operator": "DATA4",
        "aliases": ["DATA4 Cornaredo", "DATA4", "DATA 4 MILAN", "D4 Data Center MIL1"],
    },
    "Retelit Avalon 3": {
        "operator": "Retelit",
        "aliases": ["Retelit Avalon 3", "Avalon 3", "Retelit"],
    },
    "ROM1": {
        "operator": "Digital Realty",
        "aliases": ["ROM1", "Digital Realty ROM1", "Rom1"],
    },
    "Apto Lacchiarella": {
        "operator": "APTO",
        "aliases": ["Apto Lacchiarella", "APTO", "Lacchiarella"],
    },
    "Aruba Roma Tecnopolo Tiburtino": {
        "operator": "Aruba",
        "aliases": ["Aruba Roma Tecnopolo Tiburtino", "Aruba", "Tecnopolo Tiburtino"],
    },
    "Stack Campus Siziano": {
        "operator": "STACK Infrastructure",
        "aliases": ["Stack Campus Siziano", "STACK", "Infrastructure Italia Land 2", "Siziano"],
    },
    "AWS Zibido San Giacomo": {
        "operator": "AWS",
        "aliases": ["AWS Zibido San Giacomo", "AWS", "Amazon Data Services", "Zibido San Giacomo"],
    },
    "Noovle Data Center": {
        "operator": "Noovle",
        "aliases": ["Noovle Data Center", "Noovle"],
    },
    "Data Center Campus 133 Generatori": {
        "operator": "KRYALOS SGR S.p.A.",
        "aliases": ["Data Center Campus 133 Generatori", "KRYALOS", "Vimercate", "133 generatori"],
    },
}


MASE_ID_TO_PROJECT = {
    "10198": "Vantage MXP2",
    "10745": "Equinix ML9",
    "10977": "CyrusOne MIL1",
    "11218": "Noovle Data Center",
    "11308": "Aruba Roma Tecnopolo Tiburtino",
    "11503": "Apto Lacchiarella",
    "11512": "DATA4 Cornaredo",
    "11703": "Stack Campus Siziano",
    "11794": "Equinix ML5-ML6",
    "11813": "Data Center Campus 133 Generatori",
    "11899": "Equinix ML10-ML11",
    "11965": "Equinix ML7-ML8",
    "11970": "AWS Zibido San Giacomo",
    "11998": "DATA4 Cornaredo",
    "12068": "Retelit Avalon 3",
    "8791": "Microsoft Bornasco",
}


URL_PROJECT_RULES = [
    ("techbau.it/realizzazioni/ml9", "Equinix ML9"),
    ("techbau.it/realizzazioni/ml8", "Equinix ML7-ML8"),
    ("techbau.it/realizzazioni/ml7", "Equinix ML7-ML8"),
    ("techbau.it/realizzazioni/digital-realty-rom1", "ROM1"),
    ("techbau.it/en/2025/12/11/techbau-selected-to-deliver-digital-realtys-rom1", "ROM1"),
    ("techbau.it/realizzazioni/vantage", "Vantage MXP2"),
    ("techbau.it/en/2026/03/26/cyrusone-mil1", "CyrusOne MIL1"),
    ("generaleprefabbricatispa.com/storie/campus-data-center-data4", "DATA4 Cornaredo"),
    ("mercuryeng.com/project/odn-2-1-hyper-scale-data-centre", "Stack Campus Siziano"),
]


GENERIC_PROJECTS = {
    "",
    "mission critical",
    "data center",
    "datacenter",
}


BAD_URL_FRAGMENTS = [
    "realizzazioni-logistica",
    "realizzazioni-studentati",
    "realizzazioni-energie-rinnovabili",
    "realizzazioni-hotel",
    "realizzazioni-industriale",
    "realizzazioni-residenziale",
    "realizzazioni-uffici",
    "realizzazioni-retail",
    "italiandatacenter.com",
    "datacenternation.com",
    "mailto:",
    "tel:",
]


def clean(value: object) -> str:
    return str(value or "").strip()


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        clean(r.get("mase_object_id")): r
        for r in rows
        if clean(r.get("mase_object_id"))
    }


def parse_int(value: object) -> int:
    try:
        return int(float(clean(value).replace(",", ".")))
    except Exception:
        return 0


def add_unique(values: list[str], value: object) -> None:
    value = clean(value)
    if value and value not in values:
        values.append(value)


def normalize_measure_value(value: object) -> str:
    value = clean(value).replace(",", ".")

    if not value:
        return ""

    try:
        n = float(value)
        if n.is_integer():
            return str(int(n))
        return str(n).rstrip("0").rstrip(".")
    except Exception:
        return clean(value)


def add_unique_measure(values: list[str], value: object) -> None:
    value = normalize_measure_value(value)
    if value and value not in values:
        values.append(value)


def join(values: list[str], sep: str = " | ", limit: int | None = None) -> str:
    cleaned = []
    for v in values:
        v = clean(v)
        if v and v not in cleaned:
            cleaned.append(v)

    if limit is not None:
        cleaned = cleaned[:limit]

    return sep.join(cleaned)


def first(values: list[str], fallback: str = "") -> str:
    for v in values:
        if clean(v):
            return clean(v)
    return fallback


def source_url_is_bad(url: str) -> bool:
    low = clean(url).lower()
    return any(fragment in low for fragment in BAD_URL_FRAGMENTS)


def project_from_url(url: str) -> str:
    low = clean(url).lower()
    for fragment, project in URL_PROJECT_RULES:
        if fragment in low:
            return project
    return ""


def find_canonical_from_text(*values: str) -> str:
    blob = norm(" ".join(clean(v) for v in values if clean(v)))
    if not blob:
        return ""

    best_project = ""
    best_score = 0

    for canonical, meta in CANONICAL.items():
        aliases = [canonical] + meta["aliases"]
        score = 0

        for alias in aliases:
            a = norm(alias)
            if not a:
                continue

            if a == blob:
                score += 100
            elif a in blob:
                score += 70

            a_terms = set(a.split())
            b_terms = set(blob.split())
            score += len(a_terms & b_terms) * 12

            a_codes = {t for t in a_terms if any(ch.isdigit() for ch in t)}
            b_codes = {t for t in b_terms if any(ch.isdigit() for ch in t)}
            score += len(a_codes & b_codes) * 35

        if score > best_score:
            best_score = score
            best_project = canonical

    return best_project if best_score >= 55 else ""


def canonical_from_public_lead(row: dict[str, str]) -> str:
    project = clean(row.get("project"))
    developer = clean(row.get("developer"))
    location = clean(row.get("location"))
    lead_type = clean(row.get("lead_type"))
    url = clean(row.get("source_url"))

    url_project = project_from_url(url)
    if url_project:
        return url_project

    if source_url_is_bad(url):
        return ""

    if norm(project) in GENERIC_PROJECTS:
        return ""

    if "watchlist" in norm(lead_type):
        return ""

    # Non usare evidence/keyword_hits per decidere il progetto:
    # servono solo dopo, quando il progetto è già agganciato.
    return find_canonical_from_text(project, developer, location)


def extract_mw_it_candidates(text: str) -> list[str]:
    out = []
    text = clean(text)

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*MW\s*IT",
        r"(\d+(?:[.,]\d+)?)\s*megawatt\s*\(MW\)",
        r"capacità\s+IT\s+complessiva\s+di\s+(\d+(?:[.,]\d+)?)\s*MW",
        r"capacity\s+of\s+(\d+(?:[.,]\d+)?)\s*MW",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            add_unique(out, m.group(1).replace(",", "."))

    return out


def extract_area_candidates(text: str) -> list[str]:
    out = []
    text = clean(text)

    patterns = [
        r"(\d{1,3}(?:[.]\d{3})+|\d+)\s*mq",
        r"(\d{1,3}(?:[.]\d{3})+|\d+)\s*m²",
        r"(\d{1,3}(?:[.]\d{3})+|\d+)\s*sqm",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = m.group(1).replace(".", "")
            add_unique(out, value)

    return out


def confidence_label(grade: str, status: str) -> str:
    if grade == "A":
        return "Consolidato"
    if grade == "B":
        return "Da verificare"
    if grade == "C":
        return "Parziale"
    if grade == "D" and status == "external_sources_needed":
        return "Fonti esterne necessarie"
    if grade == "D":
        return "Debole"
    return "Da classificare"


def business_priority(grade: str, action_priority: str) -> str:
    if action_priority == "P1":
        return "Alta"
    if action_priority == "P2":
        return "Media"
    if grade == "A":
        return "Monitoraggio"
    return "Bassa"


def init_record(project: str) -> dict[str, object]:
    meta = CANONICAL.get(project, {})
    return {
        "project": project,
        "operator_or_main_subject": meta.get("operator", "Da identificare"),
        "operator_sources": [],
        "mase_proponents": [],
        "mase_object_ids": [],
        "mase_source_urls": [],
        "contractors": [],
        "contractor_roles": [],
        "contractor_sources": [],
        "contractor_source_urls": [],
        "contractor_confidences": [],
        "locations": [],
        "regions": [],
        "mw_it_values": [],
        "mw_it_sources": [],
        "mw_it_source_urls": [],
        "thermal_mwt_values": [],
        "thermal_mwt_sources": [],
        "thermal_mwt_source_urls": [],
        "site_area_m2_values": [],
        "site_area_sources": [],
        "site_area_source_urls": [],
        "campus_codes": [],
        "confidence_grades": [],
        "confidence_statuses": [],
        "business_statuses": [],
        "business_priorities": [],
        "missing_fields": [],
        "next_actions": [],
        "technical_notes": [],
    }


def ensure(records: dict[str, dict[str, object]], project: str) -> dict[str, object]:
    if project not in records:
        records[project] = init_record(project)
    return records[project]


def merge_mase(records: dict[str, dict[str, object]]) -> None:
    mase_rows = read_csv(MASE_DASHBOARD)
    confidence_by_id = by_id(read_csv(CONFIDENCE))
    action_by_id = by_id(read_csv(ACTION_QUEUE))
    target_by_id = by_id(read_csv(TARGETS))

    for row in mase_rows:
        object_id = clean(row.get("mase_object_id"))
        project = MASE_ID_TO_PROJECT.get(object_id) or find_canonical_from_text(
            row.get("display_project"),
            row.get("primary_developer"),
            row.get("campus_codes"),
        )

        if not project:
            continue

        rec = ensure(records, project)

        target = target_by_id.get(object_id, {})
        conf = confidence_by_id.get(object_id, {})
        action = action_by_id.get(object_id, {})

        add_unique(rec["mase_object_ids"], object_id)
        add_unique(rec["mase_source_urls"], clean(target.get("source_url")))

        add_unique(rec["mase_proponents"], row.get("primary_proponent"))
        add_unique(rec["locations"], clean(row.get("location") or target.get("location")))
        add_unique(rec["regions"], clean(row.get("region") or target.get("region")))

        add_unique_measure(rec["mw_it_values"], row.get("primary_it_power_mw"))
        if clean(row.get("primary_it_power_mw")):
            add_unique(rec["mw_it_sources"], "MASE facts")
            add_unique(rec["mw_it_source_urls"], clean(target.get("source_url")))

        add_unique_measure(rec["thermal_mwt_values"], row.get("primary_thermal_power_mwt"))
        if clean(row.get("primary_thermal_power_mwt")):
            add_unique(rec["thermal_mwt_sources"], "MASE facts")
            add_unique(rec["thermal_mwt_source_urls"], clean(target.get("source_url")))

        add_unique_measure(rec["site_area_m2_values"], row.get("primary_site_area_m2"))
        if clean(row.get("primary_site_area_m2")):
            add_unique(rec["site_area_sources"], "MASE facts")
            add_unique(rec["site_area_source_urls"], clean(target.get("source_url")))

        for code in clean(row.get("campus_codes")).split("|"):
            add_unique(rec["campus_codes"], code.strip())

        grade = clean(conf.get("confidence_grade"))
        status = clean(conf.get("confidence_status"))
        action_priority = clean(action.get("action_priority"))

        add_unique(rec["confidence_grades"], grade)
        add_unique(rec["confidence_statuses"], status)
        add_unique(rec["business_statuses"], confidence_label(grade, status))
        add_unique(rec["business_priorities"], business_priority(grade, action_priority))
        add_unique(rec["missing_fields"], action.get("missing_fields"))
        add_unique(rec["next_actions"], action.get("next_action"))
        add_unique(rec["technical_notes"], row.get("notes"))


def relation_is_usable(row: dict[str, str]) -> bool:
    lead_type = norm(row.get("lead_type"))
    role = norm(row.get("role"))
    package = norm(row.get("package"))
    url = clean(row.get("source_url"))

    if source_url_is_bad(url):
        return False

    if "watchlist" in lead_type:
        return False

    if "developer proponent" in role:
        return False

    if "contractor" in role:
        return True
    if "general contractor" in role:
        return True
    if role in {"epc", "engineering design", "engineering"}:
        return True
    if "design" in role or "engineering" in role:
        return True
    if "prefab" in role or "structural" in role:
        return True
    if "district cooling" in role or "energy" in role:
        return True

    # Se la riga è manual confirmed ed è legata a un progetto, accettala.
    if "manual confirmed contractor lead" in lead_type:
        return True

    # Accetta project page specifiche con package di costruzione.
    if "contractor project page" in lead_type and ("construction" in package or "data center" in package):
        return True

    return False


def merge_public_leads(records: dict[str, dict[str, object]]) -> None:
    for row in read_csv(PUBLIC_LEADS):
        project = canonical_from_public_lead(row)

        if not project:
            continue

        rec = ensure(records, project)

        add_unique(rec["operator_sources"], clean(row.get("developer")))
        add_unique(rec["locations"], row.get("location"))
        add_unique(rec["regions"], row.get("region"))

        source_url = clean(row.get("source_url"))
        lead_type = clean(row.get("lead_type"))
        evidence_blob = " ".join([
            clean(row.get("evidence")),
            clean(row.get("keyword_hits")),
            clean(row.get("package")),
        ])

        if relation_is_usable(row):
            company = clean(row.get("company"))
            role = clean(row.get("role"))
            package = clean(row.get("package"))
            confidence = clean(row.get("confidence"))

            if company:
                add_unique(rec["contractors"], company)
                add_unique(rec["contractor_roles"], " - ".join(v for v in [company, role, package] if v))
                add_unique(rec["contractor_sources"], lead_type)
                add_unique(rec["contractor_source_urls"], source_url)
                add_unique(rec["contractor_confidences"], confidence)

        for value in extract_mw_it_candidates(evidence_blob):
            add_unique_measure(rec["mw_it_values"], value)
            add_unique(rec["mw_it_sources"], lead_type or "public lead")
            add_unique(rec["mw_it_source_urls"], source_url)

        for value in extract_area_candidates(evidence_blob):
            add_unique_measure(rec["site_area_m2_values"], value)
            add_unique(rec["site_area_sources"], lead_type or "public lead")
            add_unique(rec["site_area_source_urls"], source_url)


def merge_matrix_only(records: dict[str, dict[str, object]]) -> None:
    for row in read_csv(ENRICHMENT_MATRIX):
        project = find_canonical_from_text(row.get("project"), row.get("mase_object_id"))

        if not project:
            continue

        rec = ensure(records, project)

        add_unique(rec["mase_object_ids"], row.get("mase_object_id"))
        add_unique(rec["next_actions"], row.get("next_enrichment_source"))

        if clean(row.get("priority")) == "P1":
            add_unique(rec["business_priorities"], "Alta")
            add_unique(rec["business_statuses"], "Fonti esterne necessarie")


def collapse_confidence(values: list[str]) -> str:
    nums = [parse_int(v) for v in values if parse_int(v) > 0]
    return str(max(nums)) if nums else ""


def final_status(grades: list[str], statuses: list[str], business_statuses: list[str]) -> str:
    order = {"A": 1, "B": 2, "C": 3, "D": 4}
    valid = [g for g in grades if clean(g)]
    if valid:
        best = sorted(valid, key=lambda g: order.get(g, 9))[0]
        if best == "A":
            return "Consolidato"
        if best == "B":
            return "Da verificare"
        if best == "C":
            return "Parziale"
        return "Fonti esterne necessarie"
    return first(business_statuses, "Da classificare")


def final_priority(priorities: list[str]) -> str:
    order = {"Alta": 1, "Media": 2, "Monitoraggio": 3, "Bassa": 4}
    values = [p for p in priorities if clean(p)]
    if not values:
        return "Media"
    return sorted(values, key=lambda p: order.get(p, 9))[0]


def to_output_rows(records: dict[str, dict[str, object]]) -> list[dict[str, str]]:
    out = []

    for project, rec in records.items():
        out.append({
            "project": project,
            "operator_or_main_subject": clean(rec["operator_or_main_subject"]),
            "operator_sources": join(rec["operator_sources"], limit=4),
            "mase_proponent": join(rec["mase_proponents"], limit=3),
            "mase_object_ids": join(rec["mase_object_ids"], limit=5),
            "mase_source_urls": join(rec["mase_source_urls"], limit=5),
            "contractor_or_partner": join(rec["contractors"], " | ", limit=5) or "Da identificare",
            "contractor_roles": join(rec["contractor_roles"], " || ", limit=6),
            "contractor_sources": join(rec["contractor_sources"], limit=5),
            "contractor_source_urls": join(rec["contractor_source_urls"], limit=5),
            "contractor_confidence": collapse_confidence(rec["contractor_confidences"]),
            "location": first(rec["locations"], "Da identificare"),
            "region": first(rec["regions"], "Da identificare"),
            "mw_it": join(rec["mw_it_values"], limit=5),
            "mw_it_sources": join(rec["mw_it_sources"], limit=5),
            "mw_it_source_urls": join(rec["mw_it_source_urls"], limit=5),
            "thermal_mwt": join(rec["thermal_mwt_values"], limit=5),
            "thermal_mwt_sources": join(rec["thermal_mwt_sources"], limit=5),
            "thermal_mwt_source_urls": join(rec["thermal_mwt_source_urls"], limit=5),
            "site_area_m2": join(rec["site_area_m2_values"], limit=5),
            "site_area_sources": join(rec["site_area_sources"], limit=5),
            "site_area_source_urls": join(rec["site_area_source_urls"], limit=5),
            "campus_codes": join(rec["campus_codes"], limit=5),
            "business_status": final_status(rec["confidence_grades"], rec["confidence_statuses"], rec["business_statuses"]),
            "business_priority": final_priority(rec["business_priorities"]),
            "confidence_grade": join(rec["confidence_grades"], limit=4),
            "missing_fields": join(rec["missing_fields"], limit=5),
            "next_action": join(rec["next_actions"], " || ", limit=5),
            "technical_notes": join(rec["technical_notes"], " || ", limit=4),
        })

    priority_order = {"Alta": 1, "Media": 2, "Monitoraggio": 3, "Bassa": 4}

    return sorted(
        out,
        key=lambda r: (
            priority_order.get(r["business_priority"], 9),
            r["region"],
            r["location"],
            r["project"].lower(),
        )
    )


def main() -> None:
    records: dict[str, dict[str, object]] = {}

    merge_mase(records)
    merge_public_leads(records)
    merge_matrix_only(records)

    rows = to_output_rows(records)

    fieldnames = [
        "project",
        "operator_or_main_subject",
        "operator_sources",
        "mase_proponent",
        "mase_object_ids",
        "mase_source_urls",
        "contractor_or_partner",
        "contractor_roles",
        "contractor_sources",
        "contractor_source_urls",
        "contractor_confidence",
        "location",
        "region",
        "mw_it",
        "mw_it_sources",
        "mw_it_source_urls",
        "thermal_mwt",
        "thermal_mwt_sources",
        "thermal_mwt_source_urls",
        "site_area_m2",
        "site_area_sources",
        "site_area_source_urls",
        "campus_codes",
        "business_status",
        "business_priority",
        "confidence_grade",
        "missing_fields",
        "next_action",
        "technical_notes",
    ]

    write_csv(OUTPUT, rows, fieldnames)

    JSON_OUTPUT.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[OK] Written {OUTPUT} with {len(rows)} rows")
    print(f"[OK] Written {JSON_OUTPUT}")


if __name__ == "__main__":
    main()
