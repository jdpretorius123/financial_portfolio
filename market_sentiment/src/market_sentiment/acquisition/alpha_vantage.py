"""Fetches news sentiment data from Alpha Vantage for selected tech tickers.

Uses the Alpha Vantage NEWS_SENTIMENT endpoint to retrieve news sentiment
data for 10 tech tickers of my choice.

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

Functions:
    fetch_ticker(): Fetch news sentiment data for one ticker.
    fetch_all_tickers(): Fetch news sentiment data for all tickers.
    config_alpha_vantage_call(): Configure the Alpha Vantage API call.
"""

import os
import time

import requests
from requests import RequestException
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from market_sentiment.warehouse.fetch import FetchFailure, FetchResult

_AV_RATE_LIMIT_DELAY = 5.0


def fetch_ticker(
    session: requests.Session, api_params: dict[str, str]
) -> FetchResult | FetchFailure:
    """Fetch news sentiment data for one ticker.

    Returns a FetchResult on a usable API response, or a FetchFailure
    for any unusable API response. A failed API response can result
    from a poor network connection, HTTP error, data decoding issue,
    rate-limit notice from Alpha Vantage, empty payload, or schema deviation.
    Every failure path is documented by a FetchFailure instance.

    Args:
        session (requests.Session): Configured requests Session used for the API call.
        api_params (dict[str, str]): API call information including the endpoint
            URL, fetch date, and Alpha Vantage query parameters.

    Returns:
        FetchResult on success; FetchFailure on any error.
    """
    params = {
        "function": api_params["function"],
        "tickers": api_params["tickers"],
        "topics": api_params["topics"],
        "time_from": api_params["time_from"],
        "sort": api_params["sort"],
        "limit": api_params["limit"],
        "apikey": api_params["apikey"],
    }
    source = "AlphaVantage"

    try:
        response = session.get(
            api_params["endpoint_url"],
            params=params,
            timeout=(5, 30),
        )
    except RequestException as conn_err:
        error_message = f"Network error contacting Alpha Vantage: {conn_err}"
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["tickers"],
            http_status="Unknown",
            error_message=error_message,
            error_type="network",
            unusable_data=None,
        )

    http_status = str(response.status_code)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        error_message = f"HTTP error from Alpha Vantage: {http_err}"
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["tickers"],
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
            ticker=api_params["tickers"],
            http_status=http_status,
            error_message=error_message,
            error_type="decode",
            unusable_data=response.text,
        )

    if "Information" in data or "Note" in data:
        error_message = f"Rate limit reached: {data}"
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["tickers"],
            http_status=http_status,
            error_message=error_message,
            error_type="rate_limit",
            unusable_data=data,
        )

    if not data:
        error_message = f"Empty data response: {data}"
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["tickers"],
            http_status=http_status,
            error_message=error_message,
            error_type="empty_payload",
            unusable_data=data,
        )

    expected_keys = {
        "items",
        "sentiment_score_definition",
        "relevance_score_definition",
        "feed",
    }
    missing_keys = expected_keys - set(data.keys())
    if missing_keys:
        error_message = f"Missing expected keys in response: {missing_keys}."
        print(error_message)
        return FetchFailure(
            fetch_date=api_params["fetch_date"],
            source=source,
            ticker=api_params["tickers"],
            http_status=http_status,
            error_message=error_message,
            error_type="schema",
            unusable_data=data,
        )

    return FetchResult(
        fetch_date=api_params["fetch_date"],
        source=source,
        ticker=api_params["tickers"],
        http_status=http_status,
        endpoint_url=api_params["endpoint_url"],
        usable_data=data,
    )


def fetch_all_tickers(
    session: requests.Session, tickers: list[str], api_information: dict[str, str]
) -> list[FetchResult | FetchFailure]:
    """Fetch news sentiment data for all tickers.

    If an individual ticker fails to fetch, a FetchFailure is returned in
    its place. The output list always has one entry per input ticker,
    preserving input order.

    Args:
        session (requests.Session): The configured requests Session used for the API
            calls.
        tickers (list[str]): The list of tech tickers to fetch.
        api_information (dict[str, str]): API call information including the endpoint
            URL, fetch date, and Alpha Vantage query parameters.

    Returns:
        One FetchResult or FetchFailure per input ticker, in input order.
    """
    all_tickers: list[FetchResult | FetchFailure] = list()

    for i, ticker in enumerate(tickers):
        if i > 0:
            time.sleep(_AV_RATE_LIMIT_DELAY)

        api_params = api_information.copy()
        api_params["tickers"] = ticker

        api_response = fetch_ticker(session, api_params)
        all_tickers.append(api_response)

    return all_tickers


def config_alpha_vantage_call(
    tickers: list[str], api_information: dict[str, str]
) -> list[FetchResult | FetchFailure]:
    """Configure the Alpha Vantage API call.

    Args:
        tickers: The list of chosen tech tickers.
        api_information: API call information including the endpoint URL,
            fetch date, and Alpha Vantage query parameters.

    Returns:
        One FetchResult or FetchFailure per input ticker.

    Raises:
        RuntimeError: If the Alpha Vantage API key is empty or missing.
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

        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not alpha_vantage_key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is empty/missing.")

        alpha_vantage_params = api_information.copy()
        alpha_vantage_params["apikey"] = alpha_vantage_key

        all_tickers = fetch_all_tickers(session, tickers, alpha_vantage_params)
    return all_tickers
