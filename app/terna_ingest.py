from pathlib import Path
import pandas as pd


INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output")


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_file = INPUT_DIR / "terna_seed_leads.csv"

    if not csv_file.exists() or csv_file.stat().st_size == 0:
        print("Nessun seed Terna trovato")
        return

    df = pd.read_csv(csv_file)
    output = OUTPUT_DIR / "terna_connection_leads.csv"
    df.to_csv(output, index=False)

    print(f"Creato {output}")


if __name__ == "__main__":
    run()
