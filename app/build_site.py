from pathlib import Path
import json
import pandas as pd


OUTPUT_DIR = Path("data/output")
DOCS_DIR = Path("docs")


def read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def records(df):
    return df.to_dict(orient="records") if not df.empty else []


def run():
    DOCS_DIR.mkdir(exist_ok=True)

    data = {
        "italy_project_summary": records(read_csv(OUTPUT_DIR / "italy_project_summary.csv")),
        "italy_developer_ranking": records(read_csv(OUTPUT_DIR / "italy_developer_ranking.csv")),
        "italy_contractor_ranking": records(read_csv(OUTPUT_DIR / "italy_contractor_ranking.csv")),
        "ecosystem_graph": records(read_csv(OUTPUT_DIR / "ecosystem_graph.csv")),
        "international_developer_ranking": records(read_csv(OUTPUT_DIR / "international_developer_ranking.csv")),
        "international_contractor_ranking": records(read_csv(OUTPUT_DIR / "international_contractor_ranking.csv")),
        "combined_leads": records(read_csv(OUTPUT_DIR / "combined_public_leads.csv")),
    }

    html = f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>DC Radar MVP</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f6f7f9; color: #1f2937; }}
    header {{ background: #111827; color: white; padding: 24px; }}
    main {{ padding: 24px; max-width: 1500px; margin: auto; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .card {{ background: white; border-radius: 14px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .num {{ font-size: 32px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #e5e7eb; font-size: 14px; text-align: left; vertical-align: top; }}
    th {{ background: #e5e7eb; }}
    section {{ margin-top: 28px; }}
    input {{ padding: 10px; width: 100%; max-width: 460px; margin: 8px 0 14px; border: 1px solid #cbd5e1; border-radius: 10px; }}
    .muted {{ color: #6b7280; }}
    .pill {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#eef2ff; font-size:12px; }}
    a {{ color:#1d4ed8; }}
  </style>
</head>
<body>
<header>
  <h1>DC Radar MVP</h1>
  <div class="muted">Vista sintetica progetti data center Italia + benchmark internazionale</div>
</header>

<main>
  <div class="grid">
    <div class="card"><div class="muted">Progetti Italia identificati</div><div class="num" id="kpiItalyProjects"></div></div>
    <div class="card"><div class="muted">MW IT noti Italia</div><div class="num" id="kpiMw"></div></div>
    <div class="card"><div class="muted">Developer Italia</div><div class="num" id="kpiDevelopers"></div></div>
    <div class="card"><div class="muted">Contractor Italia</div><div class="num" id="kpiContractors"></div></div>
  </div>

  <section>
    <h2>Progetti Data Center Italia</h2>
    <p class="muted">Dove sono i progetti, chi li propone e chi li realizza fisicamente.</p>
    <input id="filterItaly" placeholder="Filtra per progetto, comune, proponente, contractor...">
    <table id="italyTable"></table>
  </section>

  <section>
    <h2>Developer Ranking Italia</h2>
    <p class="muted">Classifica dei proponenti identificati, basata su numero progetti e MW IT noti.</p>
    <table id="italyDevTable"></table>
  </section>

  <section>
    <h2>Contractor Ranking Italia</h2>
    <p class="muted">Classifica dei soggetti che risultano coinvolti nella realizzazione fisica o tecnica.</p>
    <table id="italyContrTable"></table>
  </section>

  <section>
    <h2>Ecosistema Data Center Italia</h2>
    <p class="muted">Mappa delle relazioni: chi lavora per chi, su quale progetto e con quale ruolo.</p>
    <input id="filterGraph" placeholder="Filtra relazioni...">
    <table id="graphTable"></table>
  </section>

  <section>
    <h2>Benchmark internazionale</h2>
    <p class="muted">Vista separata: utile per capire player e contractor attivi in Europa, ma non alimenta la pipeline commerciale Italia.</p>
    <h3>Developer internazionali</h3>
    <table id="intlDevTable"></table>
    <h3>Contractor internazionali</h3>
    <table id="intlContrTable"></table>
  </section>
</main>

<script>
const DATA = {json.dumps(data, ensure_ascii=False)};

function fmt(n) {{
  const x = Number(n || 0);
  return x.toLocaleString('it-IT', {{ maximumFractionDigits: 1 }});
}}

function fmtMoney(n) {{
  const x = Number(n || 0);
  if (!x) return "";
  return x.toLocaleString('it-IT', {{ maximumFractionDigits: 0 }});
}}

function sourceLink(url) {{
  if (!url) return "";
  return `<a href="${{url}}" target="_blank">Fonte</a>`;
}}

function renderTable(id, rows, cols) {{
  const table = document.getElementById(id);
  if (!rows.length) {{
    table.innerHTML = "<tr><td>Nessun dato</td></tr>";
    return;
  }}
  table.innerHTML =
    "<thead><tr>" + cols.map(c => `<th>${{c.label}}</th>`).join("") + "</tr></thead>" +
    "<tbody>" + rows.map(r =>
      "<tr>" + cols.map(c => {{
        let value = r[c.key] ?? "";
        if (c.key === "source_url") return `<td>${{sourceLink(value)}}</td>`;
        if (c.key === "confidence") return `<td><span class="pill">${{value}}</span></td>`;
        if (c.type === "number") value = fmt(value);
        if (c.type === "money") value = fmtMoney(value);
        return `<td>${{value}}</td>`;
      }}).join("") + "</tr>"
    ).join("") + "</tbody>";
}}

function filterRows(rows, q) {{
  q = q.toLowerCase();
  if (!q) return rows;
  return rows.filter(r => JSON.stringify(r).toLowerCase().includes(q));
}}

function uniqueCount(rows, key) {{
  return new Set(rows.map(r => r[key]).filter(Boolean)).size;
}}

function init() {{
  const italy = DATA.italy_project_summary;
  const italyDev = DATA.italy_developer_ranking;
  const italyContr = DATA.italy_contractor_ranking;
  const graph = DATA.ecosystem_graph;
  const intlDev = DATA.international_developer_ranking;
  const intlContr = DATA.international_contractor_ranking;

  document.getElementById("kpiItalyProjects").textContent = italy.length;
  document.getElementById("kpiMw").textContent = fmt(italy.reduce((s,r) => s + Number(r.it_power_mw || 0), 0));
  document.getElementById("kpiDevelopers").textContent = uniqueCount(italy, "developer");
  document.getElementById("kpiContractors").textContent = uniqueCount(italy, "contractor");

  const italyCols = [
    {{key:"project", label:"Progetto"}},
    {{key:"city", label:"Comune"}},
    {{key:"province", label:"Prov."}},
    {{key:"developer", label:"Proponente / Developer"}},
    {{key:"contractor", label:"Realizzatore"}},
    {{key:"it_power_mw", label:"MW IT", type:"number"}},
    {{key:"status", label:"Stato"}},
    {{key:"source_type", label:"Fonte tipo"}},
    {{key:"confidence", label:"Conf."}},
    {{key:"source_url", label:"Link"}}
  ];

  renderTable("italyTable", italy, italyCols);

  renderTable("italyDevTable", italyDev, [
    {{key:"developer", label:"Developer"}},
    {{key:"projects_count", label:"Progetti", type:"number"}},
    {{key:"total_it_power_mw", label:"MW IT noti", type:"number"}},
    {{key:"contractors", label:"Contractor"}},
    {{key:"provinces", label:"Province"}},
    {{key:"projects", label:"Progetti"}},
    {{key:"ranking_score", label:"Score", type:"number"}}
  ]);

  renderTable("italyContrTable", italyContr, [
    {{key:"contractor", label:"Contractor"}},
    {{key:"projects_count", label:"Progetti", type:"number"}},
    {{key:"developers_count", label:"Developer", type:"number"}},
    {{key:"total_it_power_mw", label:"MW IT noti", type:"number"}},
    {{key:"developers", label:"Developer serviti"}},
    {{key:"provinces", label:"Province"}},
    {{key:"projects", label:"Progetti"}},
    {{key:"ranking_score", label:"Score", type:"number"}}
  ]);

  const graphCols = [
    {{key:"source_company", label:"Azienda"}},
    {{key:"relationship", label:"Ruolo"}},
    {{key:"target_company", label:"Cliente / Developer"}},
    {{key:"project", label:"Progetto"}},
    {{key:"location", label:"Località"}},
    {{key:"confidence", label:"Conf."}},
    {{key:"source_url", label:"Link"}}
  ];

  renderTable("graphTable", graph, graphCols);

  renderTable("intlDevTable", intlDev, [
    {{key:"developer", label:"Developer"}},
    {{key:"parent_company", label:"Parent"}},
    {{key:"projects_count", label:"Progetti", type:"number"}},
    {{key:"countries", label:"Paesi"}},
    {{key:"total_contract_value_eur", label:"Valore €", type:"money"}},
    {{key:"ranking_score", label:"Score", type:"number"}}
  ]);

  renderTable("intlContrTable", intlContr, [
    {{key:"contractor", label:"Contractor"}},
    {{key:"projects_count", label:"Progetti", type:"number"}},
    {{key:"developers_count", label:"Developer", type:"number"}},
    {{key:"countries", label:"Paesi"}},
    {{key:"total_contract_value_eur", label:"Valore €", type:"money"}},
    {{key:"ranking_score", label:"Score", type:"number"}}
  ]);

  document.getElementById("filterItaly").addEventListener("input", e => {{
    renderTable("italyTable", filterRows(italy, e.target.value), italyCols);
  }});

  document.getElementById("filterGraph").addEventListener("input", e => {{
    renderTable("graphTable", filterRows(graph, e.target.value), graphCols);
  }});
}}

init();
</script>
</body>
</html>
"""

    out = DOCS_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Creato {out}")


if __name__ == "__main__":
    run()
