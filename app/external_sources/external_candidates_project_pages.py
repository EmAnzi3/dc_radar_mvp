from __future__ import annotations

import csv
import html
import re
from datetime import datetime
from pathlib import Path


INPUT = Path("data/output/external_sources/datacentermap_promotion_draft.csv")
OUT_DIR = Path("docs/projects")


READINESS_LABELS = {
    "ready_with_gc": "Pronto con GC",
    "ready_missing_gc": "Pronto, GC da identificare",
    "partial_public_confirmation": "Conferma pubblica parziale",
    "operator_confirmed_only": "Solo operatore confermato",
    "existing_project_child_or_enrichment": "Child/enrichment progetto esistente",
    "existing_operational_reference": "Asset esistente / reference",
    "pending_validation": "Validazione pendente",
    "weak_or_no_public_evidence": "Evidenza debole",
    "not_validated": "Non validato",
}

BUCKET_LABELS = {
    "promotion_ready": "OK",
    "near_ready": "Parziale",
    "tracked_review": "Fonti ext.",
}


def clean(value: object) -> str:
    return str(value or "").strip()


def esc(value: object) -> str:
    return html.escape(clean(value), quote=True)


def norm_text(value: str) -> str:
    value = clean(value).lower()
    value = value.replace("à", "a").replace("è", "e").replace("é", "e")
    value = value.replace("ì", "i").replace("ò", "o").replace("ù", "u")
    return value


def slugify(value: str) -> str:
    value = norm_text(value)
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def read_rows() -> list[dict[str, str]]:
    if not INPUT.exists():
        raise SystemExit(f"File non trovato: {INPUT}")

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def link_button(label: str, url: str, cls: str = "") -> str:
    if not clean(url):
        return ""

    return f'<a class="btn {esc(cls)}" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def source_links_html(value: str) -> str:
    raw = clean(value)
    if not raw:
        return '<span class="muted">—</span>'

    items = []
    pos = 0

    for match in re.finditer(r"<([^<>]+)>", raw):
        label = raw[pos:match.start()].strip().strip("|").strip()
        url = match.group(1).strip()

        if label and url:
            items.append(f'<a class="source-pill" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>')

        pos = match.end()

    tail = raw[pos:].strip().strip("|").strip()
    if tail:
        items.append(f'<span class="source-pill">{esc(tail)}</span>')

    return " ".join(items) if items else '<span class="muted">—</span>'


def fact_blocks(value: str) -> str:
    facts = [clean(x) for x in clean(value).split("||") if clean(x)]

    if not facts:
        return "<p>—</p>"

    return "\n".join(f"<p>{esc(f)}</p>" for f in facts)


def badge(row: dict[str, str]) -> str:
    bucket = clean(row.get("draft_bucket"))
    readiness = clean(row.get("readiness"))

    label = BUCKET_LABELS.get(bucket, bucket or "Review")
    title = READINESS_LABELS.get(readiness, readiness)

    cls = "good" if label == "OK" else "warn" if label == "Parziale" else "neutral"

    return f'<span class="badge {cls}" title="{esc(title)}">{esc(label)}</span>'


def field(label: str, value: object) -> str:
    v = esc(value) if clean(value) else "—"
    return f"""
      <div class="field">
        <dt>{esc(label)}</dt>
        <dd>{v}</dd>
      </div>
    """


def render(row: dict[str, str]) -> str:
    name = clean(row.get("proposed_project_name"))
    generated_at = datetime.now().isoformat(timespec="seconds")

    maps = link_button("Google Maps", clean(row.get("google_maps_url")), "maps")
    dcm = link_button("DataCenterMap", clean(row.get("dcm_source_url")))

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(name)} - Data Center Radar</title>
<style>
:root {{
  --bg:#f5f7fb;
  --text:#172033;
  --muted:#667085;
  --line:#dfe4ea;
  --panel:#ffffff;
  --blue:#0f4c81;
  --dark:#08111f;
  --good-bg:#ecfdf3;
  --good:#166534;
  --warn-bg:#fff7ed;
  --warn:#92400e;
  --neutral-bg:#eff6ff;
  --neutral:#0f4c81;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  font-family:Arial,sans-serif;
  background:var(--bg);
  color:var(--text);
}}
header {{
  background:linear-gradient(135deg,var(--dark),var(--blue));
  color:white;
  padding:26px 30px;
}}
header h1 {{ margin:0; font-size:30px; }}
header p {{ margin:8px 0 0; color:#dbeafe; }}
main {{
  max-width:1300px;
  margin:0 auto;
  padding:20px;
}}
.panel {{
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:18px;
  box-shadow:0 8px 22px rgba(15,23,42,.07);
  padding:18px;
  margin-bottom:16px;
}}
.nav a {{
  color:var(--blue);
  font-weight:800;
  text-decoration:none;
}}
.badge {{
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  font-weight:800;
  font-size:12px;
}}
.badge.good {{ background:var(--good-bg); color:var(--good); }}
.badge.warn {{ background:var(--warn-bg); color:var(--warn); }}
.badge.neutral {{ background:var(--neutral-bg); color:var(--neutral); }}
.actions {{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-top:14px;
}}
.btn, .source-pill {{
  display:inline-block;
  padding:7px 11px;
  border-radius:999px;
  background:var(--neutral-bg);
  color:var(--neutral);
  text-decoration:none;
  font-weight:800;
  font-size:13px;
}}
.btn.maps {{
  background:var(--good-bg);
  color:var(--good);
}}
dl {{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin:0;
}}
.field {{
  border:1px solid var(--line);
  border-radius:14px;
  padding:12px;
  background:#fbfdff;
}}
dt {{
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.05em;
  margin-bottom:5px;
}}
dd {{
  margin:0;
  font-weight:800;
}}
h2 {{
  margin:0 0 12px;
  font-size:20px;
}}
.facts p {{
  margin:0 0 10px;
  line-height:1.45;
}}
.muted {{
  color:var(--muted);
}}
@media (max-width:900px) {{
  dl {{ grid-template-columns:1fr; }}
}}
</style>
</head>
<body>
<header>
  <h1>{esc(name)}</h1>
  <p>Scheda progetto da DataCenterMap review · generata il {esc(generated_at)}</p>
</header>
<main>
  <div class="nav panel">
    <a href="../index.html">← Torna alla dashboard principale</a>
  </div>

  <section class="panel">
    {badge(row)}
    <div class="actions">
      {maps}
      {dcm}
    </div>
  </section>

  <section class="panel">
    <h2>Dati principali</h2>
    <dl>
      {field("Operatore", row.get("operator_or_main_subject"))}
      {field("Proponente", row.get("authorization_proponent"))}
      {field("GC / contractor", row.get("contractor_or_partner"))}
      {field("Stato DCM raw", row.get("dcm_status"))}
      {field("Comune", row.get("city"))}
      {field("MW IT", row.get("it_power_mw"))}
      {field("Superficie", row.get("site_area_m2"))}
      {field("Readiness", READINESS_LABELS.get(clean(row.get("readiness")), row.get("readiness")))}
      {field("Bucket", row.get("draft_bucket"))}
    </dl>
  </section>

  <section class="panel">
    <h2>Ubicazione</h2>
    <p><strong>{esc(row.get("address")) or "—"}</strong></p>
  </section>

  <section class="panel">
    <h2>Validazione</h2>
    <dl>
      {field("Layer confermati", row.get("confirmed_layers"))}
      {field("Layer aperti", row.get("pending_layers"))}
      {field("Raccomandazione", row.get("promotion_recommendation"))}
    </dl>
  </section>

  <section class="panel facts">
    <h2>Facts sintetici</h2>
    {fact_blocks(row.get("summary_facts"))}
  </section>

  <section class="panel">
    <h2>Fonti</h2>
    <p>{source_links_html(row.get("source_links"))}</p>
  </section>
</main>
</body>
</html>
"""


def main() -> None:
    rows = read_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for row in rows:
        name = clean(row.get("proposed_project_name"))
        out = OUT_DIR / f"{slugify(name)}.html"

        html_out = render(row)
        html_out = "\n".join(line.rstrip() for line in html_out.splitlines()) + "\n"

        out.write_text(html_out, encoding="utf-8")
        print(f"[OK] Written {out}")

    print(f"[OK] Generated {len(rows)} DataCenterMap project pages")


if __name__ == "__main__":
    main()
