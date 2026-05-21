"""Fetches articles from NewsAPI for selected tickers.

Uses the NewsAPI /everything endpoint to retrieve all articles for 10 tickers of my
choice.

Four mega-cap tickers:
1. Microsoft (MSFT)
2. Google (GOOGL)
3. Amazon (AMZN)
4. Apple (AAPL)

Three mid-cap tickers:
5. Dynatrace, Inc. (DT)
6. Rambus, Inc. (RMBS)
7. Akamai Technologies, Inc. (AKAM)

Three small-cap tickers:
8. SoundHound AI, Inc. (SOUN)
9. Cellebrite DI Ltd. (CLBT)
10. Inseego Corp. (INSG)

The data for each ticker spans a month. An HTTP helper file
(warehouse/r2_uploader.py) loads the data into R2.
"""

import os

import requests
from requests import RequestException
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from market_sentiment.warehouse.fetch import FetchFailure, FetchResult


def fetch_ticker(
    session: requests.Session, api_params: dict[str, str]
) -> FetchResult | FetchFailure:
    """Fetch news sentiment data for one ticker.

    Returns a FetchResult on a usable API response, or a FetchFailure
    for any unusable API response. A failed API response can result
    from a poor network connection, HTTP error, data decoding issue,
    empty payload, or schema deviation. Every failure path is documented
    by a FetchFailure instance.

    Args:
        session (requests.Session): Configured requests Session used for the API call.
        api_params (dict[str, str]): API call information including the endpoint
            URL, fetch date, and NewsAPI query parameters.

    Returns:
        FetchResult on success; FetchFailure on any error.
    """
    params = {
        "q": api_params["q"],
        "searchIn": api_params["searchIn"],
        "from": api_params["from"],
        "to": api_params["to"],
        "language": api_params["language"],
        "sortBy": api_params["sortBy"],
        "apiKey": api_params["apiKey"],
    }
    source = "NewsAPI"

    try:
        response = session.get(
            api_params["endpoint_url"],
            params=params,
            timeout=(5, 30),
        )
    except RequestException as conn_err:
        error_message = f"Network error contacting NewsAPI: {conn_err}"
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["q"],
            http_status="Unknown",
            error_message=error_message,
            error_type="network",
            unusable_data=None,
        )

    http_status = str(response.status_code)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error from NewsAPI: {http_err}"
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["q"],
            http_status=http_status,
            error_message=error_message,
            error_type="http",
            unusable_data=response.text,
        )

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        error_message = "Failed to decode JSON from response."
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["q"],
            http_status=http_status,
            error_message=error_message,
            error_type="decode",
            unusable_data=response.text,
        )

    expected_keys = {"status", "totalResults", "articles"}
    missing_keys = expected_keys - set(data.keys())
    if missing_keys:
        error_message = f"Missing keys in response: {missing_keys}."
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["q"],
            http_status=http_status,
            error_message=error_message,
            error_type="schema",
            unusable_data=data,
        )

    return FetchResult(
        fetch_date=api_params["fetch_date"],
        source=source,
        ticker=api_params["q"],
        http_status=http_status,
        endpoint_url=api_params["endpoint_url"],
        usable_data=data,
    )


def fetch_all_tickers(
    session: requests.Session, keywords: list[str], api_information: dict[str, str]
) -> list[FetchResult | FetchFailure]:
    """Fetch NewsAPI articles for all tickers.

    If an individual ticker fails to fetch, a FetchFailure is returned in
    its place. The output list always has one entry per input ticker,
    preserving input order.

    Args:
        session: The configured requests Session used for the API calls.
        keywords: The keys words fed to NewsAPI when searching for articles referencing
            a ticker.
        api_information: API call information including the endpoint URL,
            fetch date, and NewsAPI query parameters.

    Returns:
        One FetchResult or FetchFailure per input ticker, in input order.
    """
    all_tickers: list[FetchResult | FetchFailure] = list()

    for kw in keywords:
        api_params = api_information.copy()
        api_params["q"] = kw

        api_response = fetch_ticker(session, api_params)
        all_tickers.append(api_response)

    return all_tickers


def config_news_api_call(
    keywords: list[str], api_information: dict[str, str]
) -> list[FetchResult | FetchFailure]:
    """Configure the NewsAPI call.

    Args:
        keywords: The keys words fed to NewsAPI when searching for articles referencing
            a ticker.
        api_information: API call information including the endpoint URL,
            fetch date, and NewsAPI query parameters.

    Returns:
        One FetchResult or FetchFailure per input ticker.

    Raises:
        RuntimeError: If the NewsAPI key is empty or missing.
    """
    with requests.Session() as session:
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=True,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount(api_information["endpoint_url"], adapter)

        newsapi_key = os.getenv("NEWSAPI_API_KEY")
        if not newsapi_key:
            raise RuntimeError("NEWSAPI_API_KEY is empty/missing.")

        newsapi_params = api_information.copy()
        newsapi_params["apiKey"] = newsapi_key

        all_tickers = fetch_all_tickers(session, keywords, newsapi_params)
    return all_tickers
