from app import mase_parser
from app import mase_document_parser
from app import terna_ingest
from app import query_generator
from app import local_authority_queries
from app import contractor_site_crawler
from app import project_extractor
from app import project_page_expander
from app import project_fact_extractor
from app import developer_master
from app import manual_leads


def main():
    print("=== DC RADAR MVP ===")

    mase_parser.run()
    mase_document_parser.run()
    terna_ingest.run()
    query_generator.run()
    local_authority_queries.run()
    contractor_site_crawler.run()
    project_extractor.run()
    project_page_expander.run()
    project_fact_extractor.run()
    developer_master.run()
    manual_leads.run()

    print("Pipeline completata")


if __name__ == "__main__":
    main()
