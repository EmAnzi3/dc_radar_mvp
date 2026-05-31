from pathlib import Path
import pandas as pd


OUTPUT_DIR = Path("data/output")
INPUT_DIR = Path("data/input")


def read_csv_safe(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def sort_if_possible(df: pd.DataFrame, by: list[str], ascending=True) -> pd.DataFrame:
    if df.empty:
        return df

    existing = [col for col in by if col in df.columns]

    if not existing:
        return df

    if isinstance(ascending, list):
        ascending = ascending[:len(existing)]

    return df.sort_values(by=existing, ascending=ascending)


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mase_docs = read_csv_safe(OUTPUT_DIR / "mase_documents.csv")
    mase_files = read_csv_safe(OUTPUT_DIR / "mase_document_files.csv")
    mase_leads = read_csv_safe(OUTPUT_DIR / "mase_contractor_leads.csv")
    mase_entity_hits = read_csv_safe(OUTPUT_DIR / "mase_entity_hits.csv")
    terna = read_csv_safe(OUTPUT_DIR / "terna_connection_leads.csv")

    generated_queries = read_csv_safe(OUTPUT_DIR / "generated_queries.csv")
    mase_discovery_queries = read_csv_safe(OUTPUT_DIR / "mase_discovery_queries.csv")
    local_authority_queries = read_csv_safe(OUTPUT_DIR / "local_authority_queries.csv")

    contractor_hits = read_csv_safe(OUTPUT_DIR / "contractor_site_hits.csv")
    contractor_project_leads = read_csv_safe(OUTPUT_DIR / "contractor_project_leads.csv")
    contractor_project_pages = read_csv_safe(OUTPUT_DIR / "contractor_project_pages.csv")
    contractor_project_facts = read_csv_safe(OUTPUT_DIR / "contractor_project_facts.csv")

    developer_master = read_csv_safe(OUTPUT_DIR / "developer_master.csv")
    ecosystem_graph = read_csv_safe(OUTPUT_DIR / "ecosystem_graph.csv")

    mercury_projects = read_csv_safe(OUTPUT_DIR / "mercury_projects.csv")
    international_developer_watchlist = read_csv_safe(
        OUTPUT_DIR / "international_developer_watchlist.csv"
    )
    international_developer_ranking = read_csv_safe(
        OUTPUT_DIR / "international_developer_ranking.csv"
    )
    international_contractor_ranking = read_csv_safe(
        OUTPUT_DIR / "international_contractor_ranking.csv"
    )

    ida_queries = read_csv_safe(OUTPUT_DIR / "ida_generated_queries.csv")
    ida_watchlist = read_csv_safe(OUTPUT_DIR / "ida_ecosystem_watchlist.csv")

    source_watchlist = read_csv_safe(INPUT_DIR / "source_watchlist.csv")
    manual_leads = read_csv_safe(OUTPUT_DIR / "manual_contractor_leads.csv")

    combined_rows = []

    if not developer_master.empty:
        for _, row in developer_master.iterrows():
            combined_rows.append({
                "project": row.get("project", ""),
                "developer": row.get("developer", ""),
                "location": row.get("city", ""),
                "region": row.get("region", ""),
                "lead_type": "Developer master project",
                "company": row.get("contractor", ""),
                "role": "contractor",
                "package": row.get("work_scope", ""),
                "confidence": row.get("confidence", ""),
                "evidence": "",
                "keyword_hits": "",
                "source_url": row.get("source_url", ""),
            })

    if not manual_leads.empty:
        for _, row in manual_leads.iterrows():
            combined_rows.append({
                "project": row.get("project", ""),
                "developer": row.get("developer", ""),
                "location": row.get("location", ""),
                "region": row.get("region", ""),
                "lead_type": "Manual confirmed contractor lead",
                "company": row.get("company", ""),
                "role": row.get("role", ""),
                "package": row.get("package", ""),
                "confidence": row.get("confidence", ""),
                "evidence": row.get("evidence", ""),
                "keyword_hits": "",
                "source_url": row.get("source_url", ""),
            })

    if not contractor_project_leads.empty:
        for _, row in contractor_project_leads.iterrows():
            combined_rows.append({
                "project": row.get("project", ""),
                "developer": row.get("developer", ""),
                "location": row.get("location", ""),
                "region": row.get("region", ""),
                "lead_type": "Contractor project extraction",
                "company": row.get("contractor", ""),
                "role": row.get("role", ""),
                "package": row.get("package", ""),
                "confidence": row.get("confidence", ""),
                "evidence": row.get("evidence", ""),
                "keyword_hits": row.get("keyword_hits", ""),
                "source_url": row.get("source_url", ""),
            })

    if not contractor_project_pages.empty:
        for _, row in contractor_project_pages.iterrows():
            combined_rows.append({
                "project": row.get("project", ""),
                "developer": row.get("developer", ""),
                "location": row.get("location", ""),
                "region": "",
                "lead_type": "Contractor project page",
                "company": row.get("contractor", ""),
                "role": row.get("role", ""),
                "package": row.get("package", ""),
                "confidence": row.get("confidence", ""),
                "evidence": row.get("text_sample", ""),
                "keyword_hits": row.get("keyword_hits", ""),
                "source_url": row.get("source_url", ""),
            })

    if not contractor_hits.empty:
        for _, row in contractor_hits.iterrows():
            hits = str(row.get("keyword_hits", "") or "").strip()
            if not hits:
                continue

            combined_rows.append({
                "project": "",
                "developer": "",
                "location": "",
                "region": "",
                "lead_type": "Contractor site keyword hit",
                "company": row.get("source_name", ""),
                "role": "contractor / engineering watchlist hit",
                "package": "",
                "confidence": 40,
                "evidence": row.get("text_sample", ""),
                "keyword_hits": hits,
                "source_url": row.get("url", ""),
            })

    if not mase_files.empty:
        for _, row in mase_files.iterrows():
            hits = str(row.get("keyword_hits", "") or "").strip()
            if not hits:
                continue

            combined_rows.append({
                "project": row.get("project", ""),
                "developer": row.get("developer", ""),
                "location": row.get("location", ""),
                "region": row.get("region", ""),
                "lead_type": "MASE keyword hit",
                "company": "",
                "role": "",
                "package": "",
                "confidence": 30,
                "evidence": row.get("page_text_sample", ""),
                "keyword_hits": hits,
                "source_url": row.get("document_page_url", ""),
            })

    if not terna.empty:
        for _, row in terna.iterrows():
            combined_rows.append({
                "project": row.get("project", ""),
                "developer": row.get("developer", ""),
                "location": row.get("location", ""),
                "region": row.get("region", ""),
                "lead_type": "Terna connection seed",
                "company": "",
                "role": "grid connection lead",
                "package": "electrical / HV",
                "confidence": 20,
                "evidence": row.get("notes", ""),
                "keyword_hits": "",
                "source_url": row.get("source_url", ""),
            })

    combined = pd.DataFrame(combined_rows)

    combined_path = OUTPUT_DIR / "combined_public_leads.csv"
    combined.to_csv(combined_path, index=False, encoding="utf-8-sig")

    xlsx_path = OUTPUT_DIR / "dc_radar_public_parser_report.xlsx"

    developer_master = sort_if_possible(
        developer_master,
        by=["status", "province", "it_power_mw"],
        ascending=[True, True, False],
    )

    contractor_project_facts = sort_if_possible(
        contractor_project_facts,
        by=["province", "city", "it_power_mw"],
        ascending=[True, True, False],
    )

    ecosystem_graph = sort_if_possible(
        ecosystem_graph,
        by=["confidence", "source_company", "target_company"],
        ascending=[False, True, True],
    )

    mercury_projects = sort_if_possible(
        mercury_projects,
        by=["contract_value_eur", "project"],
        ascending=[False, True],
    )

    international_developer_watchlist = sort_if_possible(
        international_developer_watchlist,
        by=["contract_value_eur", "developer", "project"],
        ascending=[False, True, True],
    )

    international_developer_ranking = sort_if_possible(
        international_developer_ranking,
        by=["ranking_score", "total_contract_value_eur"],
        ascending=[False, False],
    )

    international_contractor_ranking = sort_if_possible(
        international_contractor_ranking,
        by=["ranking_score", "total_contract_value_eur"],
        ascending=[False, False],
    )

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        combined.to_excel(writer, sheet_name="Combined Leads", index=False)

        developer_master.to_excel(writer, sheet_name="Developer Master", index=False)
        ecosystem_graph.to_excel(writer, sheet_name="Ecosystem Graph", index=False)
        contractor_project_facts.to_excel(writer, sheet_name="Contractor Project Facts", index=False)

        international_developer_ranking.to_excel(
            writer,
            sheet_name="International Dev Ranking",
            index=False,
        )
        international_contractor_ranking.to_excel(
            writer,
            sheet_name="International Contr Ranking",
            index=False,
        )
        international_developer_watchlist.to_excel(
            writer,
            sheet_name="International Dev Watch",
            index=False,
        )
        mercury_projects.to_excel(writer, sheet_name="Mercury Benchmark", index=False)

        manual_leads.to_excel(writer, sheet_name="Manual Contractor Leads", index=False)
        contractor_project_pages.to_excel(writer, sheet_name="Contractor Project Pages", index=False)
        contractor_project_leads.to_excel(writer, sheet_name="Contractor Project Leads", index=False)
        contractor_hits.to_excel(writer, sheet_name="Contractor Site Hits", index=False)

        ida_watchlist.to_excel(writer, sheet_name="IDA Watchlist", index=False)
        ida_queries.to_excel(writer, sheet_name="IDA Queries", index=False)

        mase_discovery_queries.to_excel(writer, sheet_name="MASE Discovery Queries", index=False)
        generated_queries.to_excel(writer, sheet_name="Generated Queries", index=False)
        local_authority_queries.to_excel(writer, sheet_name="Local Authority Queries", index=False)
        source_watchlist.to_excel(writer, sheet_name="Source Watchlist", index=False)

        mase_docs.to_excel(writer, sheet_name="MASE Pages", index=False)
        mase_files.to_excel(writer, sheet_name="MASE Document Pages", index=False)
        mase_leads.to_excel(writer, sheet_name="MASE Contractor Leads", index=False)
        mase_entity_hits.to_excel(writer, sheet_name="MASE Entity Hits", index=False)
        terna.to_excel(writer, sheet_name="Terna Seeds", index=False)

    print(f"Creato {combined_path} ({len(combined)} righe)")
    print(f"Creato {xlsx_path}")


if __name__ == "__main__":
    run()


