"""Reads data from warehousing.

Reads raw data stored in warehousing (R2). The warehousing contents are historical
and current publications for 10 total tickers of my choice. The historical publications
have been assessed for sentiment for every ticker mentioned in the publication. This
does not apply to the current publications. The tickers are spread across three market
capitalization brackets: mega, medium, and small. Reference warehouse/r2_uploader.py
for the tickers.

Functions:
    read_ticker(): Reads content for a single ticker from warehousing.
    read_all_tickers(): Reads all content from warehousing.
    config_r2_read(): Configure the reader for retrieving warehousing content.
"""

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

from market_sentiment.warehouse._helpers import create_warehouse_key, verify_env
from market_sentiment.warehouse.result import ReadFailure, ReadResult


def read_ticker(
    read_date: str, client: S3Client, key: str, bucket_name: str
) -> ReadFailure | ReadResult:
    """Reads content for a single ticker from warehousing.

    Reads the raw data for one ticker from warehousing (R2). The details of
    the upload transaction are stored as metadata. Successful and
    unsuccessful transactions both included the date (YYYY_MM_DD), API source, ticker
    affiliated with the transaction, and HTTP status of the transaction. Successful
    transactions also contained the warehouse endpoint URL and usable data. Unsuccessful
    transactions contained the error message, error type, and unusable data.

    Args:
        read_date (str): The date of the read.
        client (S3Client): The S3 client.
        key (str): The warehousing key associated with the API transaction that
            uploaded the content into R2 for a single ticker.
        bucket_name (str): The name of the R2 bucket.

    Returns:
        ReadResult | ReadFailure: ReadResult if successful; ReadFailure otherwise.
    """
    try:
        response = client.get_object(Bucket=bucket_name, Key=key)
    except (
        ClientError,
        EndpointConnectionError,
        ConnectTimeoutError,
        ReadTimeoutError,
        NoCredentialsError,
        ParamValidationError,
        BotoCoreError,
    ) as exc:
        if isinstance(exc, ClientError):
            return ReadFailure(
                read_date=read_date,
                key=key,
                upload_metadata=None,
                error_message=exc.response["Error"]["Message"],  # type: ignore
                error_type=exc.response["Error"]["Code"],  # type: ignore
            )
        else:
            return ReadFailure(
                read_date=read_date,
                key=key,
                upload_metadata=None,
                error_message=f"{type(exc).__name__ + ' ' + str(exc)}",
                error_type=f"{type(exc).__name__}",
            )
    body = response["Body"].read()
    if body == b"":
        return ReadFailure(
            read_date=read_date,
            key=key,
            upload_metadata=None,
            error_message=f"Empty body for key: {key}.",
            error_type="EmptyBody",
        )

    return ReadResult(
        read_date=read_date,
        key=key,
        upload_metadata=response["Metadata"],
        usable_data=body,
    )


def read_all_tickers(
    read_date: str,
    client: S3Client,
    bucket_name: str,
    key_prefixes: list[str],
    fetch_date: str | None = None,
) -> list[ReadResult | ReadFailure]:
    """Reads all requested content from warehousing.

    Args:
        read_date (str): The date of the read.
        client (S3Client): The S3 client.
        bucket_name (str): The name of the R2 bucket.
        key_prefixes (list[str]): The warehousing key prefixes to inspect for objects;
            <source>/<ticker>/.
        fetch_date (str | None): The stringified date (YYYY_MM_DD) of the initial API
            transaction. If not None, initiates the fetch of a single synthesized key
            per prefix; otherwise, fetches all listed keys under a prefix.

    Returns:
        list[ReadResult | ReadFailure]: A list of ReadResults and ReadFailures.
    """
    reads: list[ReadResult | ReadFailure] = []
    for kp in key_prefixes:
        try:
            paginator = client.get_paginator("list_objects_v2")
            keys: list[str] = []
            for page in paginator.paginate(Bucket=bucket_name, Prefix=kp):
                keys.extend(obj.get("Key", "") for obj in page.get("Contents", []))
        except (
            ClientError,
            EndpointConnectionError,
            ConnectTimeoutError,
            ReadTimeoutError,
            NoCredentialsError,
            ParamValidationError,
            BotoCoreError,
        ) as exc:
            if isinstance(exc, ClientError):
                reads.append(
                    ReadFailure(
                        read_date=read_date,
                        key=kp,
                        upload_metadata=None,
                        error_message=exc.response["Error"]["Message"],  # type: ignore
                        error_type=exc.response["Error"]["Code"],  # type: ignore
                    )
                )
            else:
                reads.append(
                    ReadFailure(
                        read_date=read_date,
                        key=kp,
                        upload_metadata=None,
                        error_message=f"{type(exc).__name__ + ' ' + str(exc)}",
                        error_type=f"{type(exc).__name__}",
                    )
                )
            continue

        if not keys:
            reads.append(
                ReadFailure(
                    read_date=read_date,
                    key=kp,
                    upload_metadata=None,
                    error_message=f"No objects found under prefix: {kp}.",
                    error_type="EmptyPrefix",
                )
            )
            continue

        if fetch_date is not None:
            key = create_warehouse_key(kp, fetch_date)
            reads.append(read_ticker(read_date, client, key, bucket_name))
        else:
            for k in keys:
                reads.append(read_ticker(read_date, client, k, bucket_name))
    return reads


def config_r2_read(
    read_date: str, key_prefixes: list[str]
) -> list[ReadResult | ReadFailure]:
    """Configure the reader for retrieving warehousing content.

    Args:
        read_date (str): The date of the read.
        key_prefixes (list[str]): Warehousing key prefixes associated with the API
            transactions uploaded into the warehouse.

    Returns:
        list[ReadResult | ReadFailure]: A list of ReadResults and ReadFailures.

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
        response = read_all_tickers(read_date, s3_client, r2_bucket_name, key_prefixes)
        return response
