"""Uploads data into R2.

Uses API transaction information to create metadata that is uploaded into R2
with the API transaction data for each ticker of my choice. There are 10
total tickers in total spread across three market capitalization brackets: mega,
medium, and small.

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

Each R2 upload is designated a unique batch ID constructed from the API source
(Alpha Vantage or NewsAPI), the ticker, and the date of the upload.

Functions:
    upload_ticker(): Uploads content for a single ticker into R2.
    upload_all_tickers(): Uploads all content into R2.
    config_r2_upload(): Configure the upload of content into R2.
"""

import json
from contextlib import closing

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ParamValidationError,
    ReadTimeoutError,
)
from mypy_boto3_s3.client import S3Client

from market_sentiment.warehouse._helpers import create_batch_id, verify_env
from market_sentiment.warehouse.fetch import FetchFailure, FetchResult


def upload_ticker(
    client: S3Client, ticker: FetchFailure | FetchResult, bucket_name: str
) -> None:
    """Uploads content for a single ticker into R2.

    Uploads the API transaction information associated with one ticker into R2.
    The details of the transaction are stored as metadata. Both successful and
    unsuccessful transactions include the date (YYYY_MM_DD), API source, ticker
    affiliated with the transaction, and HTTP status of the transaction. Successful API
    transactions (FetchResult) also contain the Endpoint URL and usable data from the
    API call. Unsuccessful transactions (FetchFailure) contain the error message, error
    type, and unusable data from the API call.

    Args:
        client (S3Client): The S3 client.
        ticker (FetchFailure | FetchResult): The tech company ticker and its associated
            API transaction information and response data.
        bucket_name (str): The name of the target R2 bucket for upload.

    Returns:
        None

    Raises:
        ClientError: If there are S3 verification errors.
        ConnectTimeoutError: If TCP validation is incomplete.
        EndpointConnectionError: If the connection with client fails.
        ReadTimeoutError: If there is no response body received within the allotted
            read timeout.
        NoCredentialsError: If credentials are incorrectly specified.
        ParamValidationError: If upload parameters are incorrectly specified. Reasons
            include incorrect typing and/or schema validation.
        BotoCoreError: If botocore flags an issue with upload into R2.
    """
    content = None
    if isinstance(ticker, FetchResult):
        content = json.dumps(ticker.usable_data).encode("utf-8")
        metadata = {
            "fetch_date": ticker.fetch_date,
            "source": ticker.source,
            "ticker": ticker.ticker,
            "http_status": ticker.http_status,
            "endpoint_url": ticker.endpoint_url,
        }
    else:
        content = json.dumps(
            {
                "error_message": ticker.error_message,
                "unusable_data": ticker.unusable_data,
            }
        ).encode("utf-8")
        metadata = {
            "fetch_date": ticker.fetch_date,
            "source": ticker.source,
            "ticker": ticker.ticker,
            "http_status": ticker.http_status,
            "error_type": ticker.error_type,
        }

    if ticker.source == "AlphaVantage":
        data_desc = "news_sentiment"
    else:
        data_desc = "articles"

    batch_id = create_batch_id(
        source=ticker.source,
        ticker=ticker.ticker,
        fetch_date=ticker.fetch_date,
        data_desc=data_desc,
    )

    client.put_object(
        Bucket=bucket_name,
        Key=batch_id,
        Body=content,
        ContentType="application/json; charset=utf-8",
        Metadata=metadata,
    )


def upload_all_tickers(
    client: S3Client, content: list[FetchFailure | FetchResult], bucket_name: str
) -> list[tuple[str, str]]:
    """Uploads all content into R2.

    Uploads one FetchResult or FetchFailure per input ticker, in order,
    into R2 with a date-assigned batch ID that describes the source and data.

    Args:
        client (S3Client): The S3 client.
        content (list[FetchFailure | FetchResult]): The content uploaded into R2,
            in order; one FetchFailure or FetchResult per ticker.
        bucket_name (str): The name of the R2 bucket.

    Returns:
        list[tuple[str, str]]: A list of errors (name, message) if the upload of a
            ticker into R2 is unsuccessful; nothing if successful.
    """
    failures: list[tuple[str, str]] = []
    for ticker in content:
        try:
            upload_ticker(client, ticker, bucket_name)

        except (
            ClientError,
            EndpointConnectionError,
            ConnectTimeoutError,
            ReadTimeoutError,
            NoCredentialsError,
            ParamValidationError,
            BotoCoreError,
        ) as exc:
            failures.append((ticker.ticker, f"{type(exc).__name__}: {exc}"))
    return failures


def config_r2_upload(content: list[FetchFailure | FetchResult]) -> None:
    """Configure the upload of content into R2.

    Args:
        content (list[FetchFailure | FetchResult]): The content uploaded into R2.

    Returns:
        None

    Raises:
        RuntimeError: Initiated if an environment variable (R2 access key ID, R2 secret
            access key, R2 endpoint URL, R2 bucket name) is missing or empty.
    """
    r2_access_key_id = verify_env("R2_ACCESS_KEY_ID")
    r2_secret_access_key = verify_env("R2_SECRET_ACCESS_KEY")
    r2_endpoint_url = verify_env("R2_ENDPOINT_URL")
    r2_bucket_name = verify_env("R2_BUCKET_NAME")

    r2_config = Config(
        region_name="auto",
        retries={"max_attempts": 5, "mode": "standard"},
        max_pool_connections=20,
        connect_timeout=5,
        read_timeout=10,
    )

    with closing(
        boto3.client(  # type: ignore
            "s3",
            region_name="auto",
            endpoint_url=r2_endpoint_url,
            aws_access_key_id=r2_access_key_id,
            aws_secret_access_key=r2_secret_access_key,
            config=r2_config,
        )
    ) as s3_client:
        failures = upload_all_tickers(s3_client, content, r2_bucket_name)

        if failures:
            print(f"R2 upload failures: {len(failures)}/{len(content)} tickers.")
            for ticker_symbol, error in failures:
                print(f"{ticker_symbol}: {error}")
