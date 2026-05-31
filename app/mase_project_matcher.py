from pathlib import Path
from datetime import datetime
import re

import pandas as pd


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


def tokens(value):
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return [x for x in value.split() if len(x) >= 2]


def extract_project_codes(value):
    value = clean(value).lower()
    return re.findall(r"\b(?:ml|rom|mxp)\d+\b", value)


def score_match(project_row, mase_row):
    project = clean(project_row.get("project", ""))
    city = clean(project_row.get("city", ""))
    province = clean(project_row.get("province", ""))
    developer = clean(project_row.get("developer", ""))
    contractor = clean(project_row.get("contractor", ""))

    blob = " ".join([
        clean(mase_row.get("title", "")),
        clean(mase_row.get("project", "")),
        clean(mase_row.get("developer", "")),
        clean(mase_row.get("proponent", "")),
        clean(mase_row.get("location", "")),
        clean(mase_row.get("location_hints", "")),
        clean(mase_row.get("keyword_hits", "")),
        clean(mase_row.get("text_sample", "")),
        clean(mase_row.get("source_url", "")),
        clean(mase_row.get("document_page_url", "")),
    ]).lower()

    score = 0
    evidence = []

    project_low = project.lower()
    city_low = city.lower()
    province_low = province.lower()
    developer_low = developer.lower()
    contractor_low = contractor.lower()

    if project_low and project_low in blob:
        score += 55
        evidence.append("project exact")

    project_codes = extract_project_codes(project)

    for code in project_codes:
        if code in blob:
            score += 45
            evidence.append(f"project code {code}")
        else:
            score -= 60
            evidence.append(f"missing project code {code}")

    # gestione altri token progetto tipo codici brevi
    for t in tokens(project):
        if re.fullmatch(r"[a-z]{1,4}\d{1,3}", t) and t in blob and t not in project_codes:
            score += 25
            evidence.append(f"project token {t}")

    if city_low and city_low in blob:
        score += 25
        evidence.append("city")

    if province_low and f"({province_low})" in blob:
        score += 10
        evidence.append("province")

    if developer and developer.lower() not in ["da identificare", "nan", "none"]:
        dev_tokens = [t for t in tokens(developer) if len(t) >= 4]
        hit_tokens = [t for t in dev_tokens if t in blob]
        if hit_tokens:
            score += min(30, 10 * len(hit_tokens))
            evidence.append("developer tokens: " + ", ".join(hit_tokens[:5]))

    if contractor and contractor_low in blob:
        score += 10
        evidence.append("contractor")

    dc_terms = ["data center", "datacenter", "centro elaborazione dati"]
    if any(term in blob for term in dc_terms):
        score += 20
        evidence.append("data center term")

    # penalizza falsi positivi energetici
    negative_terms = [
        "impianto eolico",
        "parco eolico",
        "aerogeneratori",
        "impianto fotovoltaico",
        "agrivoltaico",
    ]
    if any(term in blob for term in negative_terms) and not any(term in blob for term in dc_terms):
        score -= 40
        evidence.append("energy false-positive penalty")

    return max(score, 0), "; ".join(evidence)


def normalize_mase_sources():
    rows = []

    docs = read_csv_safe(OUTPUT_DIR / "mase_documents.csv")
    files = read_csv_safe(OUTPUT_DIR / "mase_document_files.csv")
    discovered = read_csv_safe(OUTPUT_DIR / "mase_discovered_objects.csv")

    if not docs.empty:
        for _, r in docs.iterrows():
            rows.append({
                "source_kind": "mase_documents",
                "mase_object_id": r.get("mase_object_id", ""),
                "title": "",
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "proponent": r.get("developer", ""),
                "location": r.get("location", ""),
                "location_hints": r.get("location", ""),
                "keyword_hits": r.get("keyword_hits", ""),
                "text_sample": "",
                "source_url": r.get("source_url", ""),
                "document_page_url": r.get("document_url", ""),
            })

    if not files.empty:
        for _, r in files.iterrows():
            rows.append({
                "source_kind": "mase_document_files",
                "mase_object_id": r.get("mase_object_id", ""),
                "title": r.get("file_title", ""),
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "proponent": r.get("developer", ""),
                "location": r.get("location", ""),
                "location_hints": r.get("location", ""),
                "keyword_hits": r.get("keyword_hits", ""),
                "text_sample": r.get("page_text_sample", ""),
                "source_url": r.get("document_page_url", ""),
                "document_page_url": r.get("document_page_url", ""),
            })

    if not discovered.empty:
        for _, r in discovered.iterrows():
            rows.append({
                "source_kind": "mase_discovered_objects",
                "mase_object_id": r.get("mase_object_id", ""),
                "title": r.get("title", ""),
                "project": "",
                "developer": "",
                "proponent": r.get("proponent", ""),
                "location": "",
                "location_hints": r.get("location_hints", ""),
                "keyword_hits": r.get("keyword_hits", ""),
                "text_sample": r.get("text_sample", ""),
                "source_url": r.get("source_url", ""),
                "document_page_url": "",
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).fillna("")


def run():
    summary = read_csv_safe(OUTPUT_DIR / "italy_project_summary.csv")
    mase_sources = normalize_mase_sources()

    out = OUTPUT_DIR / "mase_project_matches.csv"

    if summary.empty or mase_sources.empty:
        pd.DataFrame().to_csv(out, index=False, encoding="utf-8-sig")
        print(f"Creato {out} (0 match)")
        return

    rows = []

    for _, p in summary.iterrows():
        best = []

        for _, m in mase_sources.iterrows():
            score, evidence = score_match(p, m)

            if score >= 90:
                best.append({
                    "project": p.get("project", ""),
                    "city": p.get("city", ""),
                    "province": p.get("province", ""),
                    "developer_current": p.get("developer", ""),
                    "contractor": p.get("contractor", ""),
                    "mase_object_id": m.get("mase_object_id", ""),
                    "mase_proponent": m.get("proponent", ""),
                    "mase_title": m.get("title", ""),
                    "match_score": score,
                    "match_evidence": evidence,
                    "source_kind": m.get("source_kind", ""),
                    "source_url": m.get("source_url", ""),
                    "document_page_url": m.get("document_page_url", ""),
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                })

        best = sorted(best, key=lambda x: x["match_score"], reverse=True)

        for item in best[:5]:
            rows.append(item)

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values(by=["project", "match_score"], ascending=[True, False])
        df = df.drop_duplicates(subset=["project", "mase_object_id", "source_kind", "source_url"])
    else:
        df = pd.DataFrame(columns=[
            "project", "city", "province", "developer_current", "contractor",
            "mase_object_id", "mase_proponent", "mase_title", "match_score",
            "match_evidence", "source_kind", "source_url", "document_page_url",
            "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} match)")


if __name__ == "__main__":
    run()

