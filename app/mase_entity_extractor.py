from pathlib import Path
from datetime import datetime
import re
import pandas as pd


OUTPUT_DIR = Path("data/output")


ENTITY_PATTERNS = [
    "Microsoft",
    "Vantage",
    "Apto",
    "Techbau",
    "Jacobs",
    "Arup",
    "AECOM",
    "DBA",
    "Schneider",
    "Vertiv",
    "Terna",
    "Enel",
    "A2A",
    "Italgas",
    "Snam",
    "proponente",
    "committente",
    "progettista",
    "direttore lavori",
    "general contractor",
    "impresa",
    "appaltatore",
    "subappaltatore",
    "gruppi elettrogeni",
    "cabina",
    "connessione",
]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def hits(text):
    low = text.lower()
    return "; ".join([p for p in ENTITY_PATTERNS if p.lower() in low])


def extract_snippet(text, term, radius=220):
    low = text.lower()
    idx = low.find(term.lower())
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(term) + radius)
    return clean(text[start:end])


def run():
    src = OUTPUT_DIR / "mase_document_files.csv"
    out = OUTPUT_DIR / "mase_entity_hits.csv"

    if not src.exists() or src.stat().st_size == 0:
        print("Nessun mase_document_files.csv trovato")
        return

    df = pd.read_csv(src).fillna("")
    rows = []

    for _, r in df.iterrows():
        text = clean(r.get("page_text_sample", ""))
        found = hits(text)

        if not found:
            continue

        for term in found.split("; "):
            rows.append({
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "location": r.get("location", ""),
                "region": r.get("region", ""),
                "mase_object_id": r.get("mase_object_id", ""),
                "entity_or_keyword": term,
                "snippet": extract_snippet(text, term),
                "source_url": r.get("document_page_url", ""),
                "confidence": 40,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    if rows:
        out_df = pd.DataFrame(rows).drop_duplicates(
            subset=["project", "entity_or_keyword", "source_url", "snippet"]
        )
    else:
        out_df = pd.DataFrame()

    out_df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(out_df)} righe)")


if __name__ == "__main__":
    run()
