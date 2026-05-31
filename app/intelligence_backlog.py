from pathlib import Path
from datetime import datetime
import pandas as pd

INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")

def run():
    src = INPUT_DIR / "open_intelligence_targets.csv"
    out = OUTPUT_DIR / "intelligence_backlog.csv"

    if not src.exists() or src.stat().st_size == 0:
        print("Nessun open_intelligence_targets.csv trovato")
        return

    df = pd.read_csv(src).fillna("")
    df["checked_at"] = datetime.now().isoformat(timespec="seconds")
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} righe)")

if __name__ == "__main__":
    run()
