from pathlib import Path
from datetime import datetime
import re

import pandas as pd
from pypdf import PdfReader


OUTPUT_DIR = Path("data/output")


KEYWORDS = [
    "proponente",
    "committente",
    "progettista",
    "direttore lavori",
    "general contractor",
    "appaltatore",
    "subappaltatore",
    "impresa",
    "data center",
    "datacenter",
    "cabina",
    "connessione",
    "gruppi elettrogeni",
    "generatori",
    "potenza",
    "particella",
    "mappale",
    "catastale",
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


def keyword_hits(text):
    low = text.lower()
    return "; ".join([k for k in KEYWORDS if k in low])


def extract_pdf_text(path: Path):
    reader = PdfReader(str(path))
    pages = []

    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""

        txt = clean(txt)

        if txt:
            pages.append((i, txt))

    return pages


def run():
    src = OUTPUT_DIR / "mase_pdf_files.csv"
    out = OUTPUT_DIR / "mase_pdf_text.csv"

    pdfs = read_csv_safe(src)
    rows = []

    if pdfs.empty:
        print("Nessun mase_pdf_files.csv trovato")
        pd.DataFrame().to_csv(out, index=False, encoding="utf-8-sig")
        return

    for _, r in pdfs.iterrows():
        local_path = Path(str(r.get("local_path", "")))

        if not local_path.exists() or local_path.suffix.lower() != ".pdf":
            continue

        print(f"MASE PDF TEXT: {local_path}")

        try:
            pages = extract_pdf_text(local_path)
            error = ""
        except Exception as exc:
            pages = []
            error = str(exc)

        if not pages:
            rows.append({
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "location": r.get("location", ""),
                "region": r.get("region", ""),
                "mase_object_id": r.get("mase_object_id", ""),
                "pdf_url": r.get("pdf_url", ""),
                "local_path": str(local_path),
                "page": "",
                "keyword_hits": "",
                "text_sample": "",
                "error": error or "Nessun testo estratto",
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
            continue

        for page_num, text in pages:
            hits = keyword_hits(text)

            if not hits:
                continue

            rows.append({
                "project": r.get("project", ""),
                "developer": r.get("developer", ""),
                "location": r.get("location", ""),
                "region": r.get("region", ""),
                "mase_object_id": r.get("mase_object_id", ""),
                "pdf_url": r.get("pdf_url", ""),
                "local_path": str(local_path),
                "page": page_num,
                "keyword_hits": hits,
                "text_sample": text[:2500],
                "error": "",
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })

    if rows:
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=[
            "project", "developer", "location", "region", "mase_object_id",
            "pdf_url", "local_path", "page", "keyword_hits",
            "text_sample", "error", "checked_at"
        ])

    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()
