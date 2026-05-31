from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/local_authority_top_queries.csv")
OUTPUT = Path("data/input/local_authority_source_results.csv")


FIELDNAMES = [
    "rank",
    "project",
    "priority",
    "source_level",
    "source_name",
    "query",
    "search_url",
    "purpose",
    "checked",
    "result_status",
    "result_url",
    "result_title",
    "evidence_type",
    "extracted_facts",
    "next_action",
    "notes",
    "created_at",
    "updated_at",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clean(value: object) -> str:
    return str(value or "").strip()


def key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        clean(row.get("project")).lower(),
        clean(row.get("source_level")).lower(),
        clean(row.get("query")).lower(),
    )


def main() -> None:
    top_queries = read_csv(INPUT)
    existing_rows = read_csv(OUTPUT)

    existing_by_key = {key(row): row for row in existing_rows}

    now = datetime.now().isoformat(timespec="seconds")
    output_rows = []

    for q in top_queries:
        k = key(q)
        old = existing_by_key.get(k, {})

        row = {
            "rank": clean(q.get("rank")),
            "project": clean(q.get("project")),
            "priority": clean(q.get("priority")),
            "source_level": clean(q.get("source_level")),
            "source_name": clean(q.get("source_name")),
            "query": clean(q.get("query")),
            "search_url": clean(q.get("search_url")),
            "purpose": clean(q.get("purpose")),
            "checked": clean(old.get("checked")) or "no",
            "result_status": clean(old.get("result_status")),
            "result_url": clean(old.get("result_url")),
            "result_title": clean(old.get("result_title")),
            "evidence_type": clean(old.get("evidence_type")),
            "extracted_facts": clean(old.get("extracted_facts")),
            "next_action": clean(old.get("next_action")),
            "notes": clean(old.get("notes")),
            "created_at": clean(old.get("created_at")) or now,
            "updated_at": now if old else "",
        }

        output_rows.append(row)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] Written {OUTPUT} with {len(output_rows)} rows")


if __name__ == "__main__":
    main()
