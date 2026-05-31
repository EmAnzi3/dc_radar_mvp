from pathlib import Path
from datetime import datetime
import pandas as pd

INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")

def run():
    src = INPUT_DIR / "local_authority_backlog.csv"
    out = OUTPUT_DIR / "local_authority_backlog.csv"

    if not src.exists():
        print("Nessun local_authority_backlog.csv trovato")
        return

    df = pd.read_csv(src).fillna("")

    df["checked_at"] = datetime.now().isoformat(timespec="seconds")

    df.to_csv(
        out,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Creato {out} ({len(df)} righe)")

if __name__ == "__main__":
    run()
