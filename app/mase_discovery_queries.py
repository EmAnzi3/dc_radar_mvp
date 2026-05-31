from pathlib import Path
from datetime import datetime
import pandas as pd


OUTPUT_DIR = Path("data/output")


MASE_INFO_DOMAIN = "site:va.mite.gov.it/it-IT/Oggetti/Info"
MASE_DOC_DOMAIN = "site:va.mite.gov.it/it-IT/Oggetti/Documentazione"


TARGETS = [
    {
        "project": "ML8",
        "city": "Settimo Milanese",
        "developer_hint": "Equinix",
        "priority": "high",
        "notes": "Developer mancante; possibile fascicolo MASE da identificare",
    },
    {
        "project": "ML9",
        "city": "Settimo Milanese",
        "developer_hint": "Equinix Hyperscale 2 (ML9) Srl",
        "priority": "high",
        "notes": "MASE 10745 già individuato manualmente",
    },
    {
        "project": "Vantage MXP2",
        "city": "Settimo Milanese",
        "developer_hint": "Vantage Data Centers Europe",
        "priority": "high",
        "notes": "MASE 10198 già collegato a generatori 143 MWt",
    },
    {
        "project": "Microsoft Bornasco",
        "city": "Bornasco",
        "developer_hint": "Microsoft",
        "priority": "medium",
        "notes": "MASE 8791 già noto",
    },
    {
        "project": "CyrusOne MIL1",
        "city": "Milano",
        "developer_hint": "CyrusOne",
        "priority": "medium",
        "notes": "Verificare eventuali fascicoli MASE / Regione / SUAP",
    },
    {
        "project": "ROM1",
        "city": "Roma",
        "developer_hint": "Digital Realty",
        "priority": "medium",
        "notes": "Verificare iter autorizzativo ROM1",
    },
]


COMMON_TERMS = [
    "data center",
    "datacenter",
    "centro elaborazione dati",
    "gruppi elettrogeni",
    "generatori",
    "emergenza",
    "potenza termica",
    "AIA",
    "VIA",
    "verifica di assoggettabilità",
    "proponente",
]


def q(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if " " in value:
        return f'"{value}"'
    return value


def add_query(rows, target, query_type, query):
    rows.append({
        "project": target["project"],
        "city": target["city"],
        "developer_hint": target["developer_hint"],
        "priority": target["priority"],
        "query_type": query_type,
        "query": query,
        "notes": target["notes"],
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    })


def build_queries(target):
    rows = []
    project = target["project"]
    city = target["city"]
    dev = target["developer_hint"]

    base_terms = [
        project,
        city,
        dev,
        f"{project} {city}",
        f"{dev} {city}",
    ]

    for term in base_terms:
        if term:
            add_query(rows, target, "mase_info_direct", f"{MASE_INFO_DOMAIN} {q(term)}")
            add_query(rows, target, "mase_doc_direct", f"{MASE_DOC_DOMAIN} {q(term)}")

    for common in COMMON_TERMS:
        add_query(rows, target, "mase_info_combo", f"{MASE_INFO_DOMAIN} {q(city)} {q(common)}")
        add_query(rows, target, "mase_doc_combo", f"{MASE_DOC_DOMAIN} {q(city)} {q(common)}")

    for common in COMMON_TERMS:
        if dev:
            add_query(rows, target, "mase_developer_combo", f"{MASE_INFO_DOMAIN} {q(dev)} {q(common)}")

    # Query web generiche, perché Google spesso trova meglio gli Oggetti MASE rispetto al sito stesso.
    add_query(rows, target, "web_mase_object", f'{q(project)} {q(city)} "va.mite.gov.it"')
    add_query(rows, target, "web_mase_object", f'{q(dev)} {q(city)} "va.mite.gov.it"')
    add_query(rows, target, "web_mase_object", f'{q(city)} "data center" "va.mite.gov.it"')
    add_query(rows, target, "web_mase_object", f'{q(city)} "gruppi elettrogeni" "va.mite.gov.it"')

    return rows


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for target in TARGETS:
        rows.extend(build_queries(target))

    df = pd.DataFrame(rows).drop_duplicates(subset=["project", "query"])
    out = OUTPUT_DIR / "mase_discovery_queries.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} query)")


if __name__ == "__main__":
    run()
