from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path


SEED_FACTS = Path("tmp/local_authority_probe/seed/seed_facts_consolidated.csv")
ACTS_EVIDENCE = Path("tmp/local_authority_probe/acts/acts_evidence.csv")

OUT_CSV = Path("data/output/external_sources/external_facts_review.csv")
OUT_HTML = Path("reports/site/external_sources/external_facts_review.html")


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_row(rows: list[dict[str, str]], **kwargs: str) -> None:
    row = {
        "source_layer": "",
        "project": "",
        "fact_type": "",
        "fact_value": "",
        "review_status": "",
        "confidence": "",
        "source_count": "",
        "sources": "",
        "source_urls": "",
        "usage_note": "",
        "notes": "",
        "promote_to_master": "no",
    }
    row.update(kwargs)
    rows.append(row)


def build_rows() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    for r in read_csv(SEED_FACTS):
        status = clean(r.get("consolidated_status"))
        fact_type = clean(r.get("fact_type"))

        if status == "ready":
            review_status = "ready_for_review"
        elif fact_type == "area_m2":
            review_status = "needs_semantic_qualification"
        else:
            review_status = "review_required"

        add_row(
            out,
            source_layer="company_seed",
            project=clean(r.get("project")),
            fact_type=fact_type,
            fact_value=clean(r.get("fact_value")),
            review_status=review_status,
            confidence=clean(r.get("max_confidence")),
            source_count=clean(r.get("source_count")),
            sources=clean(r.get("sources")),
            source_urls=clean(r.get("source_urls")),
            usage_note=clean(r.get("usage_note")),
            notes=clean(r.get("notes")),
        )

    seen_acts = set()

    for r in read_csv(ACTS_EVIDENCE):
        key = (
            clean(r.get("project_hint")),
            clean(r.get("candidate_status")),
            clean(r.get("strong_terms")),
            clean(r.get("url")),
        )
        if key in seen_acts:
            continue
        seen_acts.add(key)

        status = clean(r.get("candidate_status"))

        add_row(
            out,
            source_layer="local_act",
            project=clean(r.get("project_hint")),
            fact_type="local_authority_evidence",
            fact_value=clean(r.get("strong_terms")),
            review_status="ready_for_review" if status == "known_project_enrichment" else "review_required",
            confidence="85" if status == "known_project_enrichment" else "60",
            source_count="1",
            sources=clean(r.get("domain_group")),
            source_urls=clean(r.get("url")),
            usage_note="Usare come evidenza locale/amministrativa nella scheda progetto; non come dato tecnico principale.",
            notes=clean(r.get("support_terms")),
        )

    return sorted(
        out,
        key=lambda r: (
            r["project"].lower(),
            r["source_layer"],
            r["review_status"],
            r["fact_type"],
            r["fact_value"],
        ),
    )


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    trs = []

    for r in rows:
        links = []
        for i, url in enumerate([u.strip() for u in r["source_urls"].split("|") if u.strip()][:4], start=1):
            links.append(f'<a href="{e(url)}" target="_blank" rel="noopener">fonte {i}</a>')

        trs.append(f"""
        <tr>
          <td>{e(r["source_layer"])}</td>
          <td>{e(r["project"])}</td>
          <td>{e(r["fact_type"])}</td>
          <td><strong>{e(r["fact_value"])}</strong></td>
          <td>{e(r["review_status"])}</td>
          <td class="num">{e(r["confidence"])}%</td>
          <td>{e(r["sources"])}</td>
          <td>{" ".join(links)}</td>
          <td>{e(r["usage_note"])}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>External Facts Review</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1500px; margin:0 auto; padding:20px; }}
.panel {{ background:white; border:1px solid #dfe4ea; border-radius:14px; padding:16px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; vertical-align:top; text-align:left; }}
th {{ color:#667085; font-size:11px; text-transform:uppercase; }}
.num {{ text-align:right; }}
a {{ color:#0f4c81; font-weight:700; }}
</style>
</head>
<body>
<header>
<h1>External Facts Review</h1>
<p>Review-only: company seed + local acts · {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="panel">
<table>
<thead>
<tr>
<th>Layer</th><th>Progetto</th><th>Tipo</th><th>Valore</th><th>Status</th><th>Conf.</th><th>Fonti</th><th>Link</th><th>Uso</th>
</tr>
</thead>
<tbody>
{''.join(trs)}
</tbody>
</table>
</section>
</main>
</body>
</html>
"""


def main() -> None:
    rows = build_rows()

    fields = [
        "source_layer",
        "project",
        "fact_type",
        "fact_value",
        "review_status",
        "confidence",
        "source_count",
        "sources",
        "source_urls",
        "usage_note",
        "notes",
        "promote_to_master",
    ]

    write_csv(OUT_CSV, rows, fields)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} rows")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
