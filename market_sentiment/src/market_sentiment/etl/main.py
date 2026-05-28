"""Reads raw warehousing contents and prepares raw data for storage.

The R2 warehouse stores news sentiment scores and articles for a selection of tech
company tickers. The data is from two sources, Alpha Vantage and NewsAPI,
and provides both a historical and current snapshot of the public's opinion of the
companies I chose.

This script initiates the reading of data from the R2 warehouse and passes the data
to Pydantic V2 models. These models uphold data contracts and transfer the data into
BigQuery storage for analysis and visualization.
"""

import logging
import pathlib
from datetime import UTC, datetime

from dotenv import load_dotenv

from market_sentiment.etl._helpers import prepare_bq_data, upload_bq_data
from market_sentiment.warehouse import r2_reader
from market_sentiment.warehouse.result import ReadFailure, ReadResult

logger = logging.getLogger(__name__)


def main() -> None:
    """Execute data import from warehousing and transfer into storage.

    Initiates the acquisition of data from warehousing (R2) and its
    processing and transfer into storage (BigQuery).
    """
    load_dotenv()

    read_date = datetime.now(UTC).strftime("%Y_%m_%d")
    key_prefixes = [
        "AlphaVantage/",
        "NewsAPI/",
    ]

    pathlib.Path("log").mkdir(exist_ok=True)

    log_file = f"log/log_{read_date}.txt"
    logging.basicConfig(
        filename=log_file,
        # level=logging.DEBUG,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    raw_content = r2_reader.config_r2_read(read_date, key_prefixes)

    alpha_vantage_responses: list[ReadResult] = []
    newsapi_responses: list[ReadResult] = []
    failed_reads: list[ReadFailure] = []

    for rc in raw_content:
        if isinstance(rc, ReadResult):
            if rc.upload_metadata["source"] == "AlphaVantage":
                alpha_vantage_responses.append(rc)
            if rc.upload_metadata["source"] == "NewsAPI":
                newsapi_responses.append(rc)
        else:
            failed_reads.append(rc)
            logger.warning(
                "Key: %s\n\nError Type: %s\n\nError Msg: %s\n\n",
                rc.key,
                rc.error_type,
                rc.error_message,
            )

    bq_data = prepare_bq_data(alpha_vantage_responses, newsapi_responses)
    for k in list(bq_data.keys())[0:5]:
        logger.debug(f"Key: {k}\n\nValue: {bq_data[k]}\n\n")

    bq_project = "market-sentiment-intelligence"
    dataset = "market_sentiment"
    table_id = "article_sentiment"
    upload_bq_data(bq_project, dataset, table_id, bq_data)

    # logger.debug(
    #     "Batch Summary: total=%s, AV=%s, NewsAPI=%s, failed=%s",
    #     len(raw_content),
    #     len(alpha_vantage_responses),
    #     len(newsapi_responses),
    #     len(failed_reads),
    # )

    logger.info(
        "Batch Summary: total=%s, AV=%s, NewsAPI=%s, failed=%s",
        len(raw_content),
        len(alpha_vantage_responses),
        len(newsapi_responses),
        len(failed_reads),
    )


# Executing the program
if __name__ == "__main__":
    main()
