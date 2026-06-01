from __future__ import annotations

import csv
import html
import re
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/external_sources/regional_environmental_candidates.csv")
ALIASES = Path("data/input/external_sources/known_project_aliases.csv")

OUT_CSV = Path("data/output/external_sources/regional_environmental_candidates_curated.csv")
OUT_HTML = Path("reports/site/external_sources/regional_environmental_candidates_curated.html")


def clean(value: object) -> str:
    return str(value or "").strip()


def norm(value: object) -> str:
    value = clean(value).lower()
    value = re.sub(r"[^a-z0-9àèéìòù]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


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


def alias_match(row: dict[str, str], aliases: list[dict[str, str]]) -> str:
    blob = norm(" ".join([
        row.get("strong_terms", ""),
        row.get("support_terms", ""),
        row.get("known_matches", ""),
        row.get("source_url", ""),
        row.get("snippet", ""),
    ]))

    matches = []

    for a in aliases:
        project = clean(a.get("project"))
        alias = norm(a.get("alias"))
        required_context = norm(a.get("required_context"))

        if not project or not alias:
            continue

        if alias not in blob:
            continue

        if required_context and required_context not in blob:
            continue

        if project not in matches:
            matches.append(project)

    return " | ".join(matches)


def has_real_project_signal(row: dict[str, str]) -> bool:
    blob = norm(" ".join([
        row.get("strong_terms", ""),
        row.get("support_terms", ""),
        row.get("snippet", ""),
    ]))

    return any(term in blob for term in [
        "data center",
        "datacenter",
        "centro elaborazione dati",
        "hyperscale",
        "server farm",
        "cloud generatori",
        "cloud potenza termica",
    ])


def curate_status(row: dict[str, str], matched_project: str) -> tuple[str, str, str]:
    raw_status = clean(row.get("candidate_status"))

    if raw_status == "reference_policy_review":
        return "reference_policy_review", "P3", "use_as_context"

    if matched_project:
        return "known_project_match_review", "P2", "enrich_existing_project"

    if raw_status == "new_candidate_review" and has_real_project_signal(row):
        return "new_candidate_review", "P1", "manual_review_new_candidate"

    return "discard_or_low_relevance", "P4", "discard"


def dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    out = []

    for r in rows:
        key = (
            clean(r.get("region")),
            clean(r.get("curated_status")),
            clean(r.get("matched_project")),
            clean(r.get("source_url")),
            clean(r.get("strong_terms")),
        )

        if key in seen:
            continue

        seen.add(key)
        out.append(r)

    order = {
        "new_candidate_review": 0,
        "known_project_match_review": 1,
        "reference_policy_review": 2,
        "discard_or_low_relevance": 3,
    }

    return sorted(
        out,
        key=lambda r: (
            order.get(r["curated_status"], 9),
            r["region"],
            r["matched_project"],
            r["source_url"],
        ),
    )


def build_rows() -> list[dict[str, str]]:
    aliases = read_csv(ALIASES)
    rows = []

    for r in read_csv(INPUT):
        matched_project = alias_match(r, aliases)
        curated_status, priority, decision = curate_status(r, matched_project)

        rows.append({
            "region": clean(r.get("region")),
            "source_system": clean(r.get("source_system")),
            "source_type": clean(r.get("source_type")),
            "raw_status": clean(r.get("candidate_status")),
            "curated_status": curated_status,
            "review_priority": priority,
            "decision": decision,
            "matched_project": matched_project,
            "strong_terms": clean(r.get("strong_terms")),
            "support_terms": clean(r.get("support_terms")),
            "known_matches_raw": clean(r.get("known_matches")),
            "source_url": clean(r.get("source_url")),
            "snippet": clean(r.get("snippet")),
            "checked_at": clean(r.get("checked_at")),
        })

    return dedupe(rows)


def render_html(rows: list[dict[str, str]]) -> str:
    def e(value: object) -> str:
        return html.escape(clean(value))

    trs = []

    for r in rows:
        trs.append(f"""
        <tr>
          <td>{e(r["region"])}</td>
          <td>{e(r["source_system"])}</td>
          <td>{e(r["source_type"])}</td>
          <td>{e(r["curated_status"])}</td>
          <td>{e(r["review_priority"])}</td>
          <td>{e(r["decision"])}</td>
          <td>{e(r["matched_project"])}</td>
          <td>{e(r["strong_terms"])}</td>
          <td>{e(r["support_terms"])}</td>
          <td><a href="{e(r["source_url"])}" target="_blank" rel="noopener">apri</a></td>
          <td>{e(r["snippet"])}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Regional Environmental Candidates · Curated</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#f5f7fb; color:#172033; }}
header {{ background:linear-gradient(135deg,#08111f,#0f4c81); color:white; padding:24px 30px; }}
main {{ max-width:1500px; margin:0 auto; padding:20px; }}
.panel {{ background:white; border:1px solid #dfe4ea; border-radius:14px; padding:16px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; vertical-align:top; text-align:left; }}
th {{ color:#667085; font-size:11px; text-transform:uppercase; }}
a {{ color:#0f4c81; font-weight:700; }}
</style>
</head>
<body>
<header>
<h1>Regional Environmental Candidates · Curated</h1>
<p>Output regionale ripulito · {e(datetime.now().isoformat(timespec="seconds"))}</p>
</header>
<main>
<section class="panel">
<table>
<thead>
<tr>
<th>Regione</th><th>Sistema</th><th>Tipo</th><th>Status</th><th>Priorità</th><th>Decisione</th><th>Match progetto</th><th>Strong</th><th>Support</th><th>URL</th><th>Snippet</th>
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
        "region",
        "source_system",
        "source_type",
        "raw_status",
        "curated_status",
        "review_priority",
        "decision",
        "matched_project",
        "strong_terms",
        "support_terms",
        "known_matches_raw",
        "source_url",
        "snippet",
        "checked_at",
    ]

    write_csv(OUT_CSV, rows, fields)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(rows), encoding="utf-8")

    print(f"[OK] Written {OUT_CSV} with {len(rows)} curated rows")
    print(f"[OK] Written {OUT_HTML}")


if __name__ == "__main__":
    main()
