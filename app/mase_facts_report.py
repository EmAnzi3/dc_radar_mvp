from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from datetime import datetime


INPUT = Path("data/output/mase_project_facts_dashboard.csv")

SITE_DIRS = [
    Path("reports/site"),
    Path("docs"),
]

HTML_NAME = "mase_facts.html"
JSON_NAME = "mase_project_facts_dashboard.json"


def esc(value: str | None) -> str:
    return html.escape(str(value or "").strip())


def read_rows() -> list[dict[str, str]]:
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT}")

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def badge(status: str) -> str:
    status = (status or "").strip().lower()
    if status == "ready":
        return '<span class="badge ready">ready</span>'
    if status == "needs_review":
        return '<span class="badge review">needs review</span>'
    return f'<span class="badge neutral">{esc(status or "n/a")}</span>'


def split_pipe(value: str) -> str:
    parts = [p.strip() for p in (value or "").split("|") if p.strip()]
    if not parts:
        return ""
    return "".join(f"<span class='chip'>{esc(p)}</span>" for p in parts)


def clean_trailing_whitespace(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines) + "\n"


def render_html(rows: list[dict[str, str]]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total = len(rows)
    ready = sum(1 for r in rows if (r.get("quality_status") or "").lower() == "ready")
    with_it = sum(1 for r in rows if r.get("primary_it_power_mw"))
    with_thermal = sum(1 for r in rows if r.get("primary_thermal_power_mwt"))

    cards = []
    table_rows = []

    for r in rows:
        project = esc(r.get("display_project"))
        mase_id = esc(r.get("mase_object_id"))
        proponent = esc(r.get("primary_proponent"))
        developer = esc(r.get("primary_developer"))
        campus = split_pipe(r.get("campus_codes"))
        it_mw = esc(r.get("primary_it_power_mw"))
        thermal = esc(r.get("primary_thermal_power_mwt"))
        site_area = esc(r.get("primary_site_area_m2"))
        utilities = split_pipe(r.get("utilities"))
        consultants = split_pipe(r.get("consultants"))
        catasto = esc(r.get("catasto"))
        notes = esc(r.get("notes"))

        cards.append(f"""
        <article class="card">
          <div class="card-head">
            <div>
              <h2>{project}</h2>
              <p class="muted">MASE ID {mase_id}</p>
            </div>
            {badge(r.get("quality_status", ""))}
          </div>

          <dl class="facts">
            <div><dt>Developer</dt><dd>{developer}</dd></div>
            <div><dt>Proponente</dt><dd>{proponent}</dd></div>
            <div><dt>Campus</dt><dd>{campus}</dd></div>
            <div><dt>MW IT</dt><dd>{it_mw or "—"}</dd></div>
            <div><dt>MWt</dt><dd>{thermal or "—"}</dd></div>
            <div><dt>Superficie m²</dt><dd>{site_area or "—"}</dd></div>
            <div><dt>Utilities</dt><dd>{utilities or "—"}</dd></div>
            <div><dt>Consulenti</dt><dd>{consultants or "—"}</dd></div>
            <div><dt>Catasto</dt><dd>{catasto or "—"}</dd></div>
          </dl>

          <p class="notes">{notes}</p>
        </article>
        """)

        table_rows.append(f"""
        <tr>
          <td>{project}</td>
          <td>{mase_id}</td>
          <td>{developer}</td>
          <td>{proponent}</td>
          <td>{esc(r.get("campus_codes"))}</td>
          <td class="num">{it_mw}</td>
          <td class="num">{thermal}</td>
          <td>{badge(r.get("quality_status", ""))}</td>
        </tr>
        """)

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DC Radar · MASE Facts</title>
  <style>
    :root {{
      --bg: #f6f7fb;
      --card: #ffffff;
      --text: #172033;
      --muted: #657186;
      --border: #dfe4ee;
      --accent: #1f4fd8;
      --ready-bg: #dff7e8;
      --ready-text: #116b35;
      --review-bg: #fff1cc;
      --review-text: #8a5a00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      padding: 28px 22px 18px;
      max-width: 1240px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 42px);
      letter-spacing: -0.04em;
    }}
    h2 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: -0.02em;
    }}
    .muted {{
      margin: 4px 0 0;
      color: var(--muted);
    }}
    .topnav {{
      margin-top: 16px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .topnav a {{
      color: var(--accent);
      background: #fff;
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 600;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      max-width: 1240px;
      margin: 0 auto;
      padding: 0 22px 18px;
    }}
    .kpi {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 8px 26px rgba(20, 34, 65, 0.06);
    }}
    .kpi strong {{
      display: block;
      font-size: 28px;
      letter-spacing: -0.04em;
    }}
    .kpi span {{
      color: var(--muted);
      font-size: 13px;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 0 22px 40px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 18px;
      box-shadow: 0 8px 26px rgba(20, 34, 65, 0.06);
    }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 14px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      white-space: nowrap;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .badge.ready {{
      background: var(--ready-bg);
      color: var(--ready-text);
    }}
    .badge.review {{
      background: var(--review-bg);
      color: var(--review-text);
    }}
    .badge.neutral {{
      background: #eef1f7;
      color: var(--muted);
    }}
    .facts {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 16px;
      margin: 0;
    }}
    dt {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 3px;
    }}
    dd {{
      margin: 0;
      font-weight: 650;
      overflow-wrap: anywhere;
    }}
    .chip {{
      display: inline-block;
      padding: 4px 8px;
      margin: 0 5px 5px 0;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: #f8f9fc;
      font-size: 12px;
      font-weight: 650;
    }}
    .notes {{
      margin: 14px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .table-wrap {{
      margin-top: 22px;
      overflow-x: auto;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: 0 8px 26px rgba(20, 34, 65, 0.06);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      background: #fbfcff;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    footer {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 0 22px 28px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 820px) {{
      .kpis, .grid, .facts {{
        grid-template-columns: 1fr;
      }}
      header, main, footer, .kpis {{
        padding-left: 14px;
        padding-right: 14px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>MASE Facts</h1>
    <p class="muted">Facts strutturati estratti dai fascicoli MASE e consolidati per uso dashboard. Generato: {generated_at}</p>
    <nav class="topnav">
      <a href="index.html">← Dashboard</a>
      <a href="{JSON_NAME}">JSON dati</a>
    </nav>
  </header>

  <section class="kpis">
    <div class="kpi"><strong>{total}</strong><span>Fascicoli MASE consolidati</span></div>
    <div class="kpi"><strong>{ready}</strong><span>Record ready</span></div>
    <div class="kpi"><strong>{with_it}</strong><span>Con MW IT estratti</span></div>
    <div class="kpi"><strong>{with_thermal}</strong><span>Con MWt estratti</span></div>
  </section>

  <main>
    <section class="grid">
      {''.join(cards)}
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Progetto</th>
            <th>MASE ID</th>
            <th>Developer</th>
            <th>Proponente</th>
            <th>Campus</th>
            <th>MW IT</th>
            <th>MWt</th>
            <th>Stato</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </section>
  </main>

  <footer>
    Fonte: data/output/mase_project_facts_dashboard.csv
  </footer>
</body>
</html>
"""


def inject_link(index_path: Path) -> None:
    if not index_path.exists():
        return

    txt = index_path.read_text(encoding="utf-8", errors="ignore")

    if HTML_NAME in txt:
        return

    link = """
<div style="position:fixed;right:18px;bottom:18px;z-index:9999">
  <a href="mase_facts.html" style="display:inline-block;padding:10px 14px;border-radius:999px;background:#1f4fd8;color:#fff;text-decoration:none;font-family:system-ui,sans-serif;font-weight:700;box-shadow:0 8px 22px rgba(0,0,0,.18)">MASE Facts</a>
</div>
"""

    if "</body>" in txt:
        txt = txt.replace("</body>", link + "\n</body>")
    else:
        txt += link

    index_path.write_text(txt, encoding="utf-8")


def main() -> None:
    rows = read_rows()
    html_doc = clean_trailing_whitespace(render_html(rows))

    for site_dir in SITE_DIRS:
        site_dir.mkdir(parents=True, exist_ok=True)

        html_path = site_dir / HTML_NAME
        json_path = site_dir / JSON_NAME

        html_path.write_text(html_doc, encoding="utf-8")
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

        inject_link(site_dir / "index.html")

        print(f"[OK] Written {html_path}")
        print(f"[OK] Written {json_path}")

    print(f"[OK] MASE facts report generated from {INPUT}")


if __name__ == "__main__":
    main()

