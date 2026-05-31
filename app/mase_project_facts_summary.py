from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/mase_project_facts.csv")
OUTPUT = Path("data/output/mase_project_facts_summary.csv")


# Regole leggere per evitare che un fascicolo erediti progetti citati solo come contesto cumulativo.
PROJECT_RULES = {
    "8791": {
        "primary_proponent_contains": ["MICROSOFT 4825"],
        "campus_keep": {"MIL05", "MIL06"},
        "developer_keywords": ["MICROSOFT"],
    },
    "10198": {
        "primary_proponent_contains": ["VDC MXP", "VANTAGE"],
        "campus_prefixes": ["MXP2"],
        "developer_keywords": ["VDC MXP", "VANTAGE"],
        "exclude_developer_keywords": ["EQUINIX", "MICROSOFT"],
    },
    "10745": {
        "primary_proponent_contains": ["EQUINIX HYPERSCALE 2", "ML9"],
        "campus_keep": {"ML9"},
        "developer_keywords": ["EQUINIX"],
        "exclude_developer_keywords": ["MICROSOFT", "VDC MXP", "VANTAGE"],
    },
    "11965": {
        "primary_proponent_contains": ["EQUINIX HYPERSCALE 2", "ML7"],
        "campus_keep": {"ML7", "ML8"},
        "developer_keywords": ["EQUINIX"],
        "exclude_developer_keywords": ["MICROSOFT", "VDC MXP", "VANTAGE"],
    },
}


NOISE_PHRASES = [
    "nello spa",
    "dichiara nello spa",
    "ha provveduto",
    "ha approfondito",
    "si impegni",
    "attesti con",
    "prevede di",
    "come precisato",
    "risposta",
    "osservazione",
    "committente",
    "cliente",
    "www.",
    "iaf e ilac",
]


def norm_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def norm_key(value: str | None) -> str:
    value = norm_text(value).upper()
    value = value.replace(".", "")
    value = value.replace("S R L", "SRL")
    value = value.replace("S P A", "SPA")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def is_noise(value: str) -> bool:
    v = norm_text(value)
    low = v.lower()

    if not v:
        return True

    if len(v) > 140:
        return True

    if any(p in low for p in NOISE_PHRASES):
        return True

    return False


def is_company_like(value: str) -> bool:
    v = norm_key(value)
    return any(x in v for x in [" SRL", " S R L", "S.R.L", " SPA", " S P A", "S.P.A", "SRL", "SPA"])


def canonical_company(value: str) -> str:
    v = norm_text(value)

    replacements = {
        "MICROSOFT .4825 ITALY S.R.L.": "MICROSOFT 4825 ITALY S.R.L.",
        "MICROSOFT 4825 Italy SRL": "MICROSOFT 4825 ITALY S.R.L.",
        "MICROSOFT 4825 ITALY srl": "MICROSOFT 4825 ITALY S.R.L.",
        "Microsoft 4825 Italy S.r.l.": "MICROSOFT 4825 ITALY S.R.L.",
        "Microsoft 4825 Italy Srl": "MICROSOFT 4825 ITALY S.R.L.",
        "VDC MXP21 Srl": "VDC MXP 21 S.r.l.",
        "VDC MXP21 S.r.l.": "VDC MXP 21 S.r.l.",
        "VDC MXP 21 Srl": "VDC MXP 21 S.r.l.",
        "Equinix Hyperscale 2 (ML9) Srl": "EQUINIX HYPERSCALE 2 (ML9) S.r.l.",
        "Equinix Hyperscale 2 (ML9) S.r.l.": "EQUINIX HYPERSCALE 2 (ML9) S.r.l.",
        "EQUINIX HYPERSCALE 2 (ML9) S.r.l.": "EQUINIX HYPERSCALE 2 (ML9) S.r.l.",
        "Equinix Hyperscale 2 (ML7) Srl": "EQUINIX HYPERSCALE 2 (ML7) S.r.l.",
        "EQUINIX HYPERSCALE 2 (ML 7) S.R.L.": "EQUINIX HYPERSCALE 2 (ML7) S.r.l.",
        "Equinix Hyperscale 2 (ML7) Srl": "EQUINIX HYPERSCALE 2 (ML7) S.r.l.",
    }

    return replacements.get(v, v)


def parse_float(value: str) -> float | None:
    v = norm_text(value).replace(".", ".").replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", v)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def extract_campus_code(value: str) -> str:
    v = norm_text(value).upper().replace(" ", "")
    m = re.search(r"\b(MIL\d+|ML\d+|MXP\d+)\b", v)
    if not m:
        return ""
    return m.group(1)


def campus_allowed(object_id: str, code: str) -> bool:
    rule = PROJECT_RULES.get(object_id, {})
    code = code.upper()

    keep = rule.get("campus_keep")
    if keep:
        return code in keep

    prefixes = rule.get("campus_prefixes", [])
    if prefixes:
        return any(code.startswith(prefix.upper()) for prefix in prefixes)

    return True


def developer_allowed(object_id: str, value: str) -> bool:
    rule = PROJECT_RULES.get(object_id, {})
    key = norm_key(value)

    excludes = rule.get("exclude_developer_keywords", [])
    if any(ex.upper() in key for ex in excludes):
        return False

    includes = rule.get("developer_keywords", [])
    if includes:
        return any(inc.upper() in key for inc in includes)

    return True


def pick_primary_proponent(object_id: str, values: list[str]) -> str:
    rule = PROJECT_RULES.get(object_id, {})
    contains = [x.upper() for x in rule.get("primary_proponent_contains", [])]

    cleaned = []
    for v in values:
        v = canonical_company(v)
        if is_noise(v):
            continue
        if not is_company_like(v):
            continue
        cleaned.append(v)

    if contains:
        preferred = [
            v for v in cleaned
            if all(c in norm_key(v) for c in contains if c.startswith("ML")) or any(c in norm_key(v) for c in contains)
        ]
        if preferred:
            return Counter(preferred).most_common(1)[0][0]

    if cleaned:
        return Counter(cleaned).most_common(1)[0][0]

    return ""


def unique_join(values: list[str], limit: int = 20) -> str:
    seen = []
    seen_keys = set()

    for v in values:
        v = norm_text(v)
        if not v:
            continue
        k = norm_key(v)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        seen.append(v)

    return " | ".join(seen[:limit])


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT}")

    rows = []
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k: norm_text(v) for k, v in row.items()}
            if row.get("fact_value"):
                rows.append(row)

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["mase_object_id"]].append(row)

    summaries = []

    for object_id, items in sorted(grouped.items()):
        first = items[0]

        by_type = defaultdict(list)
        evidence_count = Counter()
        source_pdfs = set()
        pdf_urls = set()

        for r in items:
            ft = r.get("fact_type", "")
            fv = r.get("fact_value", "")
            by_type[ft].append(fv)
            evidence_count[ft] += 1
            if r.get("source_pdf"):
                source_pdfs.add(r["source_pdf"])
            if r.get("pdf_url"):
                pdf_urls.add(r["pdf_url"])

        # Proponent
        proponent_candidates = by_type.get("proponent", []) + by_type.get("developer_or_proponent", [])
        primary_proponent = pick_primary_proponent(object_id, proponent_candidates)

        # Developers / proponents cleaned
        devs = []
        for v in by_type.get("developer_or_proponent", []):
            if is_noise(v):
                continue
            if not developer_allowed(object_id, v):
                continue
            if is_company_like(v) or any(x in norm_key(v) for x in ["VANTAGE", "EQUINIX", "MICROSOFT"]):
                devs.append(canonical_company(v))

        # Campus codes
        campus_codes = []
        for v in by_type.get("campus_code", []):
            code = extract_campus_code(v)
            if code and campus_allowed(object_id, code):
                campus_codes.append(code)

        # Consultants
        consultants = []
        for v in by_type.get("consultant", []):
            if is_noise(v):
                continue
            key = norm_key(v)
            if "DBA PRO" in key:
                consultants.append("DBA PRO S.p.A.")
            elif "RAMS&E" in v.upper() or "RAMS" in key:
                consultants.append("RAMS&E S.r.l.")
            elif "RAMBOLL" in key:
                consultants.append("Ramboll Italy S.r.l.")
            elif "DEERNS" in key:
                consultants.append("Deerns Italia S.p.A.")
            elif "INLOCO" in key:
                consultants.append("Inloco S.r.l.")
            else:
                consultants.append(v)

        # Utilities
        utilities = []
        for v in by_type.get("utility", []):
            key = norm_key(v)
            if "TERNA" in key:
                utilities.append("Terna")
            elif "ENEL" in key:
                utilities.append("Enel")
            else:
                if not is_noise(v):
                    utilities.append(v)

        # Numeric candidates
        thermal_values = []
        for v in by_type.get("thermal_power_mwt", []):
            n = parse_float(v)
            if n is not None and n >= 1:
                thermal_values.append(n)

        it_values = []
        for v in by_type.get("it_power_mw", []):
            n = parse_float(v)
            if n is not None and n >= 1:
                it_values.append(n)

        site_values = []
        for v in by_type.get("site_area_m2", []):
            n = parse_float(v)
            if n is not None and n >= 100:
                site_values.append(int(round(n)))

        catasto_values = [
            v for v in by_type.get("catasto", [])
            if not is_noise(v)
        ]

        emails = [
            v for v in by_type.get("email", [])
            if "@" in v and len(v) <= 120
        ]

        contacts = [
            v for v in by_type.get("contact_person", [])
            if not is_noise(v)
        ]

        summary = {
            "project": first.get("project", ""),
            "developer_hint": first.get("developer_hint", ""),
            "location": first.get("location", ""),
            "region": first.get("region", ""),
            "mase_object_id": object_id,
            "primary_proponent": primary_proponent,
            "developer_or_proponent_candidates": unique_join(devs),
            "campus_codes": unique_join(sorted(campus_codes)),
            "it_power_mw_candidates": unique_join([str(x).rstrip("0").rstrip(".") for x in sorted(set(it_values))]),
            "thermal_power_mwt_candidates": unique_join([str(x).rstrip("0").rstrip(".") for x in sorted(set(thermal_values))]),
            "site_area_m2_candidates": unique_join([str(x) for x in sorted(set(site_values))]),
            "catasto": unique_join(catasto_values),
            "consultants": unique_join(consultants),
            "utilities": unique_join(utilities),
            "emails": unique_join(emails),
            "contact_persons": unique_join(contacts),
            "facts_total": len(items),
            "source_pdfs_count": len(source_pdfs),
            "source_pdfs": unique_join(sorted(source_pdfs), limit=50),
            "pdf_urls": unique_join(sorted(pdf_urls), limit=50),
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }

        summaries.append(summary)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "project",
        "developer_hint",
        "location",
        "region",
        "mase_object_id",
        "primary_proponent",
        "developer_or_proponent_candidates",
        "campus_codes",
        "it_power_mw_candidates",
        "thermal_power_mwt_candidates",
        "site_area_m2_candidates",
        "catasto",
        "consultants",
        "utilities",
        "emails",
        "contact_persons",
        "facts_total",
        "source_pdfs_count",
        "source_pdfs",
        "pdf_urls",
        "checked_at",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)

    print(f"[OK] Written {OUTPUT} with {len(summaries)} project summaries")


if __name__ == "__main__":
    main()
