"""Fetches and uploads news sentiment data into R2.

The Alpha Vantage API is used to collect historical news sentiment data for 10 tech
tickers of my choice. Four tickers are for mega-cap companies, three
are for medium-cap companies, and three are for small-cap companies.

NewsAPI is used to collect recent publications (articles, periodicals, etc.)
associated with those companies.

Together, this data enables longitudinal sentiment and trend analysis for these
companies, as well hopefully help explain trends in their stock price.

This script initiates the acquisition of data from Alpha Vantage and NewsAPI for each
selected tech ticker through their respective APIs. The details from each transaction
are used to create a monthly batch ID and metadata. Batch IDs, metadata, and
usable/unusable API transaction data are uploaded into R2. Successful API transactions,
their information and usable data, are captured by the FetchResult dataclass;
unsuccessful transactions by the FetchFailure dataclass.
"""

import pathlib
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

from market_sentiment.acquisition import alpha_vantage, newsapi
from market_sentiment.warehouse import r2_uploader


def main() -> None:
    """Execute data acquisition and upload.

    Initiates the acquisition of data from Alpha Vantage and NewsAPI for each selected
    tech ticker through their respective APIs. The details from each transaction are
    used to create a monthly batch ID and metadata. Batch IDs, metadata, and
    usable/unusable API transaction data are uploaded into R2. Successful API
    transactions, their information and usable data, are captured by the FetchResult
    dataclass; unsuccessful transactions by the FetchFailure dataclass.

    Args:
        None
    """
    load_dotenv()

    fetch_date = datetime.now(UTC).strftime("%Y_%m_%d")
    start_datetime = datetime.now(UTC) - timedelta(weeks=4)

    time_from = start_datetime.strftime("%Y%m%dT%H%M")
    tickers = [
        "MSFT",
        "GOOGL",
        "AMZN",
        "AAPL",
        "DT",
        "RMBS",
        "AKAM",
        "SOUN",
        "CLBT",
        "INSG",
    ]

    start = start_datetime.strftime("%Y-%m-%d")
    to = datetime.now(UTC).strftime("%Y-%m-%d")
    keywords = [
        "MSFT",
        "GOOGL",
        "AMZN",
        "AAPL",
        "DT",
        "RMBS",
        "AKAM",
        "SOUN",
        "CLBT",
        "INSG",
    ]

    alpha_vantage_params = {
        "fetch_date": fetch_date,
        "endpoint_url": "https://www.alphavantage.co/query",
        "function": "NEWS_SENTIMENT",
        "topics": "technology",
        "time_from": time_from,
        "sort": "LATEST",
        "limit": "1000",
    }

    newsapi_params = {
        "fetch_date": fetch_date,
        "endpoint_url": "https://newsapi.org/v2/everything",
        "searchIn": "title,description,content",
        "from": start,
        "to": to,
        "language": "en",
        "sortBy": "publishedAt",
    }

    pathlib.Path("log").mkdir(exist_ok=True)
    batch_date = datetime.now(UTC).strftime("%Y_%m_%d")
    log_file = f"log/log_{batch_date}.txt"

    with open(log_file, "w") as f:
        with redirect_stdout(f):
            alpha_vantage_content = alpha_vantage.config_alpha_vantage_call(
                tickers, alpha_vantage_params
            )
            newsapi_content = newsapi.config_news_api_call(keywords, newsapi_params)
            content = alpha_vantage_content + newsapi_content
            r2_uploader.config_r2_upload(content)


# Executing the program
if __name__ == "__main__":
    main()
