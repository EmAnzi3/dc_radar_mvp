from pathlib import Path
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_file = INPUT_DIR / "manual_contractor_leads.csv"

    if not source_file.exists() or source_file.stat().st_size == 0:
        print("Nessun manual_contractor_leads.csv trovato")
        return

    df = pd.read_csv(source_file)

    out = OUTPUT_DIR / "manual_contractor_leads.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Creato {out} ({len(df)} righe)")


if __name__ == "__main__":
    run()
