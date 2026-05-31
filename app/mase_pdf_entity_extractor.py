from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")


COMPANY_PATTERNS = [
    r"\b[A-Z][A-Za-z0-9&.\- ]{2,80}\s+(?:S\.r\.l\.|Srl|S\.p\.A\.|SpA|Ltd|Limited|GmbH)\b",
    r"\b(?:Equinix|Vantage Data Centers|Microsoft|Digital Realty|DATA4|CyrusOne|Techbau|DBA PRO|DBA Pro|RAMS&E|Ramboll Italy|Terna|Enel|A2A|ARPA|ATS)\b[A-Za-z0-9&.\- ]{0,80}",
]

ENTITY_KEYWORDS = {
    "proponent": ["proponente"],
    "developer": ["data centers europe", "hyperscale", "data center"],
    "contractor": ["general contractor", "appaltatore", "impresa esecutrice", "techbau"],
    "consultant": ["studio", "consulente", "ramboll", "dba pro", "rams&e"],
    "utility": ["terna", "enel", "cabina primaria", "stazione elettrica"],
    "authority": ["ministero", "regione", "città metropolitana", "comune", "arpa", "ats"],
}

TECH_PATTERNS = [
    ("it_power_mw", r"(\d+(?:[,.]\d+)?)\s*MW\s+(?:totali\s+di\s+)?(?:carico\s+IT|IT)"),
    ("thermal_power_mw", r"energia\s+termica\s+complessiva\s+pari\s+a\s+(\d+(?:[,.]\d+)?)\s*MW"),
    ("generators_count", r"(?:n\.?|numero)\s*(\d+)\s+generatori"),
    ("generators_count", r"installazione\s+di\s+n\.?\s*(\d+)\s+generatori"),
    ("voltage_kv", r"(\d+(?:[,.]\d+)?)\s*kV"),
    ("surface_sqm", r"(\d{1,3}(?:[.\s]\d{3})+|\d{4,})\s*(?:mq|m2|m²)"),
]

PLACE_PATTERNS = [
    ("municipality", r"Comune di\s+([A-ZÀ-Ü][A-Za-zÀ-ÿ'’.\- ]{2,60})"),
    ("province", r"\(([A-Z]{2})\)"),
    ("substation", r"(?:CP|Cabina Primaria|SE|Stazione Elettrica)\s+([A-ZÀ-Ü][A-Za-zÀ-ÿ'’.\- ]{2,40})"),
]


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except Exception:
        return pd.DataFrame()


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_number(value):
    value = str(value or "").replace(".", "").replace(",", ".")
    try:
        return str(float(value))
    except Exception:
        return str(value)


def classify_company(name, context):
    n = name.lower()
    c = context.lower()

    if "proponente" in c and n in c:
        return "proponent"

    if any(x in n for x in ["terna", "enel", "a2a"]):
        return "utility"

    if any(x in n for x in ["comune", "regione", "ministero", "arpa", "ats", "città metropolitana"]):
        return "authority"

    if any(x in n for x in ["dba", "ramboll", "rams&e"]):
        return "consultant"

    if "techbau" in n:
        return "contractor"

    if any(x in n for x in ["equinix", "vantage", "microsoft", "digital realty", "data4", "cyrusone", "vdc"]):
        return "developer_or_proponent"

    for entity_type, keywords in ENTITY_KEYWORDS.items():
        if any(k in c for k in keywords):
            return entity_type

    return "company"


def add_entity(rows, r, entity_type, value, confidence, evidence):
    value = clean(value)

    if not value or len(value) < 2:
        return

    rows.append({
        "project": r.get("project", ""),
        "developer": r.get("developer", ""),
        "location": r.get("location", ""),
        "region": r.get("region", ""),
        "mase_object_id": r.get("mase_object_id", ""),
        "entity_type": entity_type,
        "entity_value": value,
        "source_pdf": r.get("local_path", ""),
        "pdf_url": r.get("pdf_url", ""),
        "page": r.get("page", ""),
        "confidence": confidence,
        "evidence": clean(evidence)[:900],
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })


def extract_from_row(rows, r):
    text = clean(r.get("text_sample", ""))

    if not text:
        return

    # Companies
    for pattern in COMPANY_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = clean(m.group(0))
            start = max(0, m.start() - 180)
            end = min(len(text), m.end() + 180)
            context = text[start:end]
            entity_type = classify_company(value, context)
            add_entity(rows, r, entity_type, value, 70, context)

    # Technical attributes
    for entity_type, pattern in TECH_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = normalize_number(m.group(1))
            start = max(0, m.start() - 180)
            end = min(len(text), m.end() + 180)
            add_entity(rows, r, entity_type, value, 80, text[start:end])

    # Places
    for entity_type, pattern in PLACE_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = clean(m.group(1))
            start = max(0, m.start() - 160)
            end = min(len(text), m.end() + 160)
            add_entity(rows, r, entity_type, value, 70, text[start:end])


def run():
    src = OUTPUT_DIR / "mase_pdf_text.csv"
    out = OUTPUT_DIR / "mase_pdf_entities.csv"

    df = read_csv_safe(src)

    rows = []

    if df.empty:
        print("Nessun mase_pdf_text.csv trovato")
        pd.DataFrame().to_csv(out, index=False, encoding="utf-8-sig")
        return

    for _, r in df.iterrows():
        extract_from_row(rows, r)

    if rows:
        out_df = pd.DataFrame(rows)
        out_df = out_df.drop_duplicates(
            subset=["project", "mase_object_id", "entity_type", "entity_value", "source_pdf", "page"]
        )
        out_df = out_df.sort_values(by=["mase_object_id", "project", "entity_type", "entity_value"])
    else:
        out_df = pd.DataFrame(columns=[
            "project", "developer", "location", "region", "mase_object_id",
            "entity_type", "entity_value", "source_pdf", "pdf_url", "page",
            "confidence", "evidence", "checked_at"
        ])

    out_df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(out_df)} entità)")


if __name__ == "__main__":
    run()
