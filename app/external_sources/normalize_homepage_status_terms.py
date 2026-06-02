from __future__ import annotations

from pathlib import Path


INDEX = Path("docs/index.html")


REPLACEMENTS = {
    "Under Construction": "In costruzione",
    "Land Banked": "Area acquisita",
    "Planned": "Pianificato",
    "Operational": "Operativo",
}


def main() -> None:
    if not INDEX.exists():
        raise SystemExit(f"File non trovato: {INDEX}")

    txt = INDEX.read_text(encoding="utf-8")

    for old, new in REPLACEMENTS.items():
        txt = txt.replace(old, new)

    txt = "\n".join(line.rstrip() for line in txt.splitlines()) + "\n"
    INDEX.write_text(txt, encoding="utf-8")

    print(f"[OK] Normalized homepage status terms in {INDEX}")


if __name__ == "__main__":
    main()
