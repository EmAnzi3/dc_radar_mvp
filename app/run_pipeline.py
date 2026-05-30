from app import mase_parser
from app import mase_document_parser
from app import terna_ingest


def main():
    print("=== DC RADAR MVP ===")

    mase_parser.run()
    mase_document_parser.run()
    terna_ingest.run()

    print("Pipeline completata")


if __name__ == "__main__":
    main()
