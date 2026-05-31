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
    "query_active",
    "created_at",
    "updated_at",
]


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        clean(row.get("project")).lower(),
        clean(row.get("source_level")).lower(),
        clean(row.get("query")).lower(),
    )


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {field: clean(row.get(field)) for field in FIELDNAMES}


def main() -> None:
    top_queries = read_csv(INPUT)
    existing_rows = read_csv(OUTPUT)

    existing_by_key = {row_key(row): row for row in existing_rows}
    current_keys = {row_key(row) for row in top_queries}

    now = datetime.now().isoformat(timespec="seconds")
    output_rows = []

    # 1) Righe attualmente generate dal motore query
    for q in top_queries:
        k = row_key(q)
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
            "query_active": "yes",
            "created_at": clean(old.get("created_at")) or now,
            "updated_at": now if old else "",
        }

        output_rows.append(row)

    # 2) Righe vecchie non più presenti nel motore query.
    # Non si cancellano: possono contenere lavoro/manual notes.
    for old in existing_rows:
        k = row_key(old)

        if k in current_keys:
            continue

        row = normalize_row(old)
        row["query_active"] = "no"
        row["updated_at"] = now
        output_rows.append(row)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"[OK] Written {OUTPUT} with {len(output_rows)} rows")
    print(f"[OK] Active queries: {sum(1 for r in output_rows if r.get('query_active') == 'yes')}")
    print(f"[OK] Preserved inactive rows: {sum(1 for r in output_rows if r.get('query_active') == 'no')}")


if __name__ == "__main__":
    main()
