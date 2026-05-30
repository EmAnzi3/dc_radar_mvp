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
        "developer_master": records(read_csv(OUTPUT_DIR / "developer_master.csv")),
        "ecosystem_graph": records(read_csv(OUTPUT_DIR / "ecosystem_graph.csv")),
        "contractor_project_facts": records(read_csv(OUTPUT_DIR / "contractor_project_facts.csv")),
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
    main {{ padding: 24px; max-width: 1400px; margin: auto; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .card {{ background: white; border-radius: 14px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .num {{ font-size: 32px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #e5e7eb; font-size: 14px; text-align: left; vertical-align: top; }}
    th {{ background: #e5e7eb; }}
    section {{ margin-top: 28px; }}
    input {{ padding: 10px; width: 100%; max-width: 420px; margin: 8px 0 14px; border: 1px solid #cbd5e1; border-radius: 10px; }}
    .muted {{ color: #6b7280; }}
  </style>
</head>
<body>
<header>
  <h1>DC Radar MVP</h1>
  <div class="muted">Dashboard locale generata automaticamente dai CSV</div>
</header>

<main>
  <div class="grid">
    <div class="card"><div class="muted">Progetti Italia</div><div class="num" id="kpiProjects"></div></div>
    <div class="card"><div class="muted">Relazioni ecosistema</div><div class="num" id="kpiEdges"></div></div>
    <div class="card"><div class="muted">MW IT noti Italia</div><div class="num" id="kpiMw"></div></div>
    <div class="card"><div class="muted">Lead complessivi</div><div class="num" id="kpiLeads"></div></div>
  </div>

  <section>
    <h2>Pipeline Italia</h2>
    <input id="filterProjects" placeholder="Filtra progetti, developer, contractor, comune...">
    <table id="projectsTable"></table>
  </section>

  <section>
    <h2>Grafo relazioni</h2>
    <input id="filterGraph" placeholder="Filtra relazioni...">
    <table id="graphTable"></table>
  </section>

  <section>
    <h2>Ranking developer internazionale</h2>
    <table id="intlDevTable"></table>
  </section>

  <section>
    <h2>Ranking contractor internazionale</h2>
    <table id="intlContrTable"></table>
  </section>
</main>

<script>
const DATA = {json.dumps(data, ensure_ascii=False)};

function fmt(n) {{
  const x = Number(n || 0);
  return x.toLocaleString('it-IT', {{ maximumFractionDigits: 1 }});
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
      "<tr>" + cols.map(c => `<td>${{r[c.key] ?? ""}}</td>`).join("") + "</tr>"
    ).join("") + "</tbody>";
}}

function filterRows(rows, q) {{
  q = q.toLowerCase();
  if (!q) return rows;
  return rows.filter(r => JSON.stringify(r).toLowerCase().includes(q));
}}

function init() {{
  const projects = DATA.developer_master;
  const graph = DATA.ecosystem_graph;
  const intlDev = DATA.international_developer_ranking;
  const intlContr = DATA.international_contractor_ranking;

  document.getElementById("kpiProjects").textContent = projects.length;
  document.getElementById("kpiEdges").textContent = graph.length;
  document.getElementById("kpiMw").textContent = fmt(projects.reduce((s,r) => s + Number(r.it_power_mw || 0), 0));
  document.getElementById("kpiLeads").textContent = DATA.combined_leads.length;

  const projectCols = [
    {{key:"developer", label:"Developer"}},
    {{key:"project", label:"Progetto"}},
    {{key:"city", label:"Comune"}},
    {{key:"province", label:"Prov."}},
    {{key:"it_power_mw", label:"MW IT"}},
    {{key:"contractor", label:"Contractor"}},
    {{key:"work_scope", label:"Scope"}},
    {{key:"status", label:"Stato"}}
  ];

  const graphCols = [
    {{key:"source_company", label:"Fonte"}},
    {{key:"relationship", label:"Relazione"}},
    {{key:"target_company", label:"Target"}},
    {{key:"project", label:"Progetto"}},
    {{key:"location", label:"Località"}},
    {{key:"confidence", label:"Conf."}}
  ];

  renderTable("projectsTable", projects, projectCols);
  renderTable("graphTable", graph, graphCols);

  renderTable("intlDevTable", intlDev, [
    {{key:"developer", label:"Developer"}},
    {{key:"parent_company", label:"Parent"}},
    {{key:"projects_count", label:"Progetti"}},
    {{key:"countries", label:"Paesi"}},
    {{key:"total_contract_value_eur", label:"Valore €"}},
    {{key:"ranking_score", label:"Score"}}
  ]);

  renderTable("intlContrTable", intlContr, [
    {{key:"contractor", label:"Contractor"}},
    {{key:"projects_count", label:"Progetti"}},
    {{key:"developers_count", label:"Developer"}},
    {{key:"countries", label:"Paesi"}},
    {{key:"total_contract_value_eur", label:"Valore €"}},
    {{key:"ranking_score", label:"Score"}}
  ]);

  document.getElementById("filterProjects").addEventListener("input", e => {{
    renderTable("projectsTable", filterRows(projects, e.target.value), projectCols);
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
