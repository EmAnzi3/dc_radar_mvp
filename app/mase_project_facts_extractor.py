from pathlib import Path
from datetime import datetime
import re

import pandas as pd


OUTPUT_DIR = Path("data/output")


KEY_COMPANIES = [
    "Microsoft 4825 Italy S.r.l.",
    "Microsoft",
    "Equinix Hyperscale 2 (ML9) Srl",
    "Equinix",
    "VDC MXP 21 S.r.l.",
    "Vantage Data Centers Europe",
    "Vantage Data Centers",
    "Techbau",
    "DBA PRO SpA",
    "DBA Pro SpA",
    "RAMS&E Srl",
    "Ramboll Italy Srl",
    "Ramboll Italy",
    "Terna",
    "Enel",
    "A2A",
    "ARPA Lombardia",
    "Regione Lombardia",
    "Città Metropolitana di Milano",
    "Provincia di Pavia",
    "Comune di Bornasco",
    "Comune di Settimo Milanese",
]

FACT_PATTERNS = [
    ("proponent", r"(?:Proponente|Denominazione)\s*:?\s*([A-Z0-9][A-Za-z0-9&.,'’()\- ]{2,120}(?:S\.r\.l\.|Srl|S\.p\.A\.|SpA|Ltd|Limited|GmbH))"),
    ("company", r"\b([A-Z][A-Za-z0-9&.'’()\- ]{2,90}\s+(?:S\.r\.l\.|Srl|S\.p\.A\.|SpA|Ltd|Limited|GmbH))\b"),
    ("thermal_power_mwt", r"(?:potenza|energia)\s+termica\s+(?:complessiva\s+)?(?:pari\s+a|superiore\s+a|di circa)?\s*(\d+(?:[,.]\d+)?)\s*MWt?"),
    ("thermal_power_mwt", r"(\d+(?:[,.]\d+)?)\s*MWt"),
    ("it_power_mw", r"(\d+(?:[,.]\d+)?)\s*MW\s+(?:totali\s+di\s+)?carico\s+IT"),
    ("generators_count", r"(?:n\.?|numero)\s*(\d+)\s+generatori"),
    ("site_area_m2", r"superficie\s+catastale\s+complessiva\s+(?:della\s+propriet[aà]\s+)?(?:è\s+)?pari\s+a\s+([\d.]+)\s*m[²2]"),
    ("site_area_m2", r"([\d.]+)\s*m[²2]"),
    ("campus_code", r"\b(MIL05|MIL06|ML7|ML8|ML9|MXP2|MXP21|MXP22|ROM1)\b"),
    ("voltage_kv", r"(\d+(?:[,.]\d+)?)\s*kV"),
    ("substation", r"(?:Cabina Primaria|CP|Stazione Elettrica|SE)\s+([A-ZÀ-Ü][A-Za-zÀ-ÿ'’.\- ]{2,50})"),
    ("procedure", r"(Verifica di assoggettabilit[aà]\s+a\s+VIA|Valutazione di Impatto Ambientale|Verifica di ottemperanza|Permesso di Costruire|SCIA|AIA|VIA)"),
    ("document_type", r"(Studio Preliminare Ambientale|Studio di Impatto Ambientale|Valutazione Previsionale di Impatto Acustico|Decreto Direttoriale|Parere n\.\s*\d+|Relazione tecnica)"),
    ("email", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    ("contact_person", r"(?:Responsabile del procedimento|Istruttore)\s*:?\s*([A-ZÀ-Ü][A-Za-zÀ-ÿ'’.\- ]{2,60})"),
    ("catasto", r"Foglio\s+n\.?\s*(\d+).*?particelle\s+n\.?\s*([0-9, e]+)"),
]


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_number(value):
    value = str(value or "").replace(".", "").replace(",", ".")
    try:
        num = float(value)
        if num.is_integer():
            return str(int(num))
        return str(num)
    except Exception:
        return str(value)


def classify_company(value):
    low = value.lower()

    if any(x in low for x in ["microsoft", "equinix", "vdc", "vantage", "digital realty", "data4", "cyrusone"]):
        return "developer_or_proponent"
    if any(x in low for x in ["techbau"]):
        return "contractor"
    if any(x in low for x in ["dba", "ramboll", "rams&e", "stantec", "jacobs", "arcadis", "rina", "deerns"]):
        return "consultant"
    if any(x in low for x in ["terna", "enel", "a2a"]):
        return "utility"
    if any(x in low for x in ["comune", "provincia", "regione", "arpa", "ats", "ministero", "città metropolitana"]):
        return "authority"

    return "company"


def confidence_for(fact_type):
    return {
        "proponent": 95,
        "company": 75,
        "developer_or_proponent": 85,
        "contractor": 85,
        "consultant": 85,
        "utility": 80,
        "authority": 75,
        "thermal_power_mwt": 90,
        "it_power_mw": 90,
        "generators_count": 90,
        "site_area_m2": 85,
        "campus_code": 85,
        "voltage_kv": 75,
        "substation": 80,
        "procedure": 80,
        "document_type": 75,
        "email": 95,
        "contact_person": 90,
        "catasto": 85,
    }.get(fact_type, 70)


def add_fact(rows, r, fact_type, value, evidence):
    value = clean(value)

    if not value:
        return

    noisy_prefixes = [
        "COMUNE DI BORNASCO - INSTALLAZIONE",
        "PROGETTO PER LA REALIZZAZIONE",
        "ARPA LOMBARDIA TABELLA",
    ]

    if any(value.upper().startswith(x) for x in noisy_prefixes):
        return

    if fact_type == "company":
        fact_type = classify_company(value)

    if fact_type in ["thermal_power_mwt", "it_power_mw", "generators_count", "site_area_m2", "voltage_kv"]:
        value = norm_number(value)

    rows.append({
        "project": r.get("project", ""),
        "developer_hint": r.get("developer", ""),
        "location": r.get("location", ""),
        "region": r.get("region", ""),
        "mase_object_id": r.get("mase_object_id", ""),
        "fact_type": fact_type,
        "fact_value": value,
        "source_pdf": r.get("local_path", ""),
        "pdf_url": r.get("pdf_url", ""),
        "page": r.get("page", ""),
        "confidence": confidence_for(fact_type),
        "evidence": clean(evidence)[:1200],
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })


def extract_known_companies(rows, r, text):
    low = text.lower()

    for company in KEY_COMPANIES:
        if company.lower() in low:
            idx = low.find(company.lower())
            start = max(0, idx - 220)
            end = min(len(text), idx + len(company) + 220)
            add_fact(rows, r, classify_company(company), company, text[start:end])


def extract_facts_from_row(rows, r):
    text = clean(r.get("text_sample", ""))

    if not text:
        return

    extract_known_companies(rows, r, text)

    for fact_type, pattern in FACT_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            if fact_type == "catasto":
                value = f"Foglio {m.group(1)} - particelle {clean(m.group(2))}"
            else:
                value = m.group(1) if m.lastindex else m.group(0)

            start = max(0, m.start() - 220)
            end = min(len(text), m.end() + 220)
            add_fact(rows, r, fact_type, value, text[start:end])


def run():
    src = OUTPUT_DIR / "mase_pdf_text.csv"
    out = OUTPUT_DIR / "mase_project_facts.csv"

    df = read_csv_safe(src)
    rows = []

    if df.empty:
        print("Nessun mase_pdf_text.csv trovato")
        pd.DataFrame().to_csv(out, index=False, encoding="utf-8-sig")
        return

    for _, r in df.iterrows():
        extract_facts_from_row(rows, r)

    if rows:
        out_df = pd.DataFrame(rows)
        out_df = out_df.drop_duplicates(
            subset=["project", "mase_object_id", "fact_type", "fact_value", "source_pdf", "page"]
        )
        out_df = out_df.sort_values(
            by=["mase_object_id", "project", "fact_type", "confidence"],
            ascending=[True, True, True, False],
        )
    else:
        out_df = pd.DataFrame(columns=[
            "project", "developer_hint", "location", "region", "mase_object_id",
            "fact_type", "fact_value", "source_pdf", "pdf_url", "page",
            "confidence", "evidence", "checked_at"
        ])

    out_df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(out_df)} fatti)")


if __name__ == "__main__":
    run()
