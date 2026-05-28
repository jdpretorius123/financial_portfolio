"""Normalizes cross-source data before upload to BigQuery.

Use data contracts constructed through Pydantic to validate Alpha Vantage
and NewsAPI data resulting in homogeneous formatting and conformity. This
facilitates downstream analysis and visualization.

Functions:
    process_str_list(): Strips, dedupes, and sorts a list.
    canonicalize_authors(): Returns article author(s) information as a cleaned, sorted
        array.
    build_text(): Combines article title and summary into one consolidated text.
    normalize_datetime(): Normalizes formatting for all article publish datetimes.
    apply_vader(): Applies VADER scoring to a piece of text.
    normalize_alpha_vantage(): Creates a normalized row for storage from raw Alpha
        Vantage responses.
    normalize_newsapi(): Creates a normalized row for storage from raw NewsAPI
        responses.
    unique_rows(): Creates a dictionary of unique rows from two dictionaries.
    prepare_bq_data(): Prepares raw warehousing data for BigQuery upload.
    upload_bq_data(): Uploads clean data into BigQuery.
"""

import hashlib
from datetime import UTC, datetime
from typing import Any

from google.cloud import bigquery
from nltk.sentiment.vader import SentimentIntensityAnalyzer  # type: ignore

from market_sentiment.etl.schemas.alpha_vantage import NewsSentimentResponse
from market_sentiment.etl.schemas.newsapi import EverythingResponse
from market_sentiment.etl.schemas.normalized import NormalizedRow
from market_sentiment.warehouse.result import ReadResult

analyzer = SentimentIntensityAnalyzer()
SCHEMA = [
    bigquery.SchemaField("row_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("provider", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("fetch_date", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("published_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("title", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("text", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("url", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source_name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("authors", "STRING", mode="REPEATED"),
    bigquery.SchemaField("ticker_sentiment_score", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("ticker_sentiment_label", "STRING", mode="NULLABLE"),
    bigquery.SchemaField(
        "topics",
        "RECORD",
        mode="REPEATED",
        fields=[
            bigquery.SchemaField("topic", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("relevance_score", "FLOAT64", mode="REQUIRED"),
        ],  # type: ignore
    ),
    bigquery.SchemaField("vader_compound", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("vader_pos", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("vader_neu", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("vader_neg", "FLOAT64", mode="REQUIRED"),
]


def process_str_list(alist: list[str]) -> list[str]:
    """Strips, dedupes, and sorts a list.

    Args:
        alist (list[str]): An uncleaned, unsorted list with duplicates.

    Returns:
        list[str]: A cleaned, deduped, sorted list.
    """
    temp_list = [item.strip() for item in alist]
    temp_list = [item for item in temp_list if item]
    temp_list = list(set(temp_list))
    temp_list.sort()
    return temp_list


def canonicalize_authors(authors: list[str] | str | None) -> list[str]:
    """Returns article author(s) information as a cleaned, sorted array.

    Args:
        authors (list[str] | str | None): Messy, unsorted author(s) information
            from an article.

    Returns:
        list[str]: A cleaned, sorted list of article authors.
    """
    if authors:
        if isinstance(authors, str):
            author_list = authors.split(",")
            author_list = process_str_list(author_list)
        else:
            author_list = process_str_list(authors)

        return author_list
    return []


def build_text(title: str, summary: str | None) -> str:
    """Combines article title and summary into one consolidated text.

    Args:
        title (str): Article title.
        summary (str | None): Article description/summary, depending on source
            (AlphaVantage versus NewsAPI).

    Returns:
        str: Consolidated text containing article title and summary.
    """
    consolidated_text = title
    if summary is not None:
        consolidated_text += f"\n\n{summary}"
    return consolidated_text


def normalize_datetime(dt: datetime) -> str:
    """Normalizes formatting for all article publish datetimes.

    Args:
        dt (datetime): Datetime when article was published.

    Returns:
        str: Stringified datetime contract when article was published.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(tz=UTC)

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_vader(text: str) -> dict[str, float]:
    """Applies VADER scoring to a piece of text.

    Args:
        text (str): Text to be scored.

    Returns:
        dict[str, float]: The four VADER scores (compound, positive, neutral, and
            negative) given to the text.
    """
    scores = analyzer.polarity_scores(text)  # type: ignore
    return scores


def normalize_alpha_vantage(responses: list[ReadResult]) -> dict[str, NormalizedRow]:
    """Creates a normalized row for storage from raw Alpha Vantage responses.

    Takes raw Alpha Vantage read responses from warehousing and normalizes them
    for storage in BigQuery.

    Args:
        responses (list[ReadResult]): Raw Alpha Vantage read responses.

    Returns:
        dict[str, NormalizedRow]: Normalized storage data.
    """
    normalized_rows: dict[str, NormalizedRow] = {}
    seen_keys: set[str] = set()
    for response in responses:
        metadata = response.upload_metadata
        news_sentiment_response = NewsSentimentResponse.model_validate_json(
            response.usable_data
        )
        for feed_item in news_sentiment_response.feed:
            text = build_text(feed_item.title, feed_item.summary)
            authors = canonicalize_authors(feed_item.authors)
            published_at = normalize_datetime(feed_item.time_published)
            vader_scores = apply_vader(text)

            for ticker in feed_item.ticker_sentiment:
                key_parts = [
                    feed_item.url,
                    feed_item.title,
                    published_at,
                    ticker.ticker,
                ]
                key = "\0".join(key_parts)

                if key not in seen_keys:
                    seen_keys.add(key)
                    arow = NormalizedRow(
                        provider="alpha_vantage",
                        ticker=ticker.ticker,
                        fetch_date=metadata["fetch_date"],
                        published_at=published_at,
                        title=feed_item.title,
                        text=text,
                        url=feed_item.url,
                        source_name=feed_item.source,
                        authors=authors,
                        ticker_sentiment_score=ticker.ticker_sentiment_score,
                        ticker_sentiment_label=ticker.ticker_sentiment_label,
                        topics=feed_item.topics,
                        vader_compound=vader_scores["compound"],
                        vader_pos=vader_scores["pos"],
                        vader_neu=vader_scores["neu"],
                        vader_neg=vader_scores["neg"],
                    )
                    normalized_rows[key] = arow
    return normalized_rows


def normalize_newsapi(responses: list[ReadResult]) -> dict[str, NormalizedRow]:
    """Creates a normalized row for storage from raw NewsAPI responses.

    Takes raw NewsAPI read responses from warehousing and normalizes them
    for storage in BigQuery.

    Args:
        responses (list[ReadResult]): Raw NewsAPI read responses.

    Returns:
        dict[str, NormalizedRow]: Normalized storage data.
    """
    normalized_rows: dict[str, NormalizedRow] = {}
    seen_keys: set[str] = set()
    for response in responses:
        metadata = response.upload_metadata
        newsapi_response = EverythingResponse.model_validate_json(response.usable_data)
        for article in newsapi_response.articles:
            text = build_text(article.title, article.description)
            published_at = normalize_datetime(article.published_at)
            authors = canonicalize_authors(article.author)
            vader_scores = apply_vader(text)

            key_parts = [article.url, article.title, published_at, metadata["ticker"]]
            key = "\0".join(key_parts)

            if key not in seen_keys:
                seen_keys.add(key)
                arow = NormalizedRow(
                    provider="newsapi",
                    ticker=metadata["ticker"],
                    fetch_date=metadata["fetch_date"],
                    published_at=published_at,
                    title=article.title,
                    text=text,
                    url=article.url,
                    source_name=article.source.name,
                    authors=authors,
                    ticker_sentiment_score=None,
                    ticker_sentiment_label=None,
                    topics=[],
                    vader_compound=vader_scores["compound"],
                    vader_pos=vader_scores["pos"],
                    vader_neu=vader_scores["neu"],
                    vader_neg=vader_scores["neg"],
                )
                normalized_rows[key] = arow
    return normalized_rows


def unique_rows(
    alpha_vantage_rows: dict[str, NormalizedRow], newsapi_rows: dict[str, NormalizedRow]
) -> dict[str, NormalizedRow]:
    """Creates a dictionary of unique entries from two dictionaries.

    Args:
        alpha_vantage_rows (dict[str, NormalizedRow]): Normalized Alpha Vantage
            response data (values) with unique row IDs (keys).
        newsapi_rows (dict[str, NormalizedRow]): Normalized NewsAPI response data
            (values) with unique row IDs (keys).

    Returns:
        dict[str, NormalizedRow]: Dictionary of unique entries (row IDs).
    """
    big_query_rows: dict[str, NormalizedRow] = {}
    for key in alpha_vantage_rows.keys():
        if key not in big_query_rows:
            big_query_rows[key] = alpha_vantage_rows[key]
    for key in newsapi_rows.keys():
        if key not in big_query_rows:
            big_query_rows[key] = newsapi_rows[key]
    return big_query_rows


def prepare_bq_data(
    alpha_vantage_responses: list[ReadResult], newsapi_responses: list[ReadResult]
) -> dict[str, NormalizedRow]:
    """Prepares raw warehousing data for BigQuery upload.

    Args:
        alpha_vantage_responses (list[ReadResult]): Raw Alpha Vantage read responses.
        newsapi_responses (list[ReadResult]): Raw NewsAPI read responses.

    Returns:
        dict[str, NormalizedRow]: Dictionary of unique entries.
    """
    alpha_vantage_rows = normalize_alpha_vantage(alpha_vantage_responses)
    newsapi_rows = normalize_newsapi(newsapi_responses)
    bigquery_data = unique_rows(alpha_vantage_rows, newsapi_rows)
    return bigquery_data


def upload_bq_data(
    bq_project: str, dataset: str, table_id: str, bq_data: dict[str, NormalizedRow]
) -> None:
    """Uploads clean data into BigQuery.

    Takes clean data and uploads it into BigQuery.

    Args:
        bq_project (str): The BigQuery project.
        dataset (str): The BigQuery project's dataset.
        table_id (str): The BigQuery dataset's table ID.
        bq_data (dict[str, NormalizedRow]): Clean data to be stored in BigQuery.
    """
    staging_table_ref = f"{bq_project}.{dataset}.{table_id}_staging"
    target_table_ref = f"{bq_project}.{dataset}.{table_id}"

    with bigquery.Client(project=bq_project) as client:
        table = bigquery.Table(target_table_ref, schema=SCHEMA)
        table = client.create_table(table, exists_ok=True)

        rows: list[dict[str, Any]] = []
        for key, row in bq_data.items():
            d = row.model_dump()
            d["row_id"] = hashlib.sha256(key.encode()).hexdigest()
            rows.append(d)

        try:
            config = bigquery.LoadJobConfig(
                schema=SCHEMA, write_disposition="WRITE_TRUNCATE"
            )
            load_job = client.load_table_from_json(
                rows, staging_table_ref, job_config=config
            )
            load_job.result()

            merge_query = f"""
                MERGE `{target_table_ref}` AS T
                USING `{staging_table_ref}` AS S
                ON T.row_id = S.row_id
                WHEN NOT MATCHED THEN INSERT ROW
            """
            client.query(merge_query).result()
        finally:
            client.delete_table(staging_table_ref, not_found_ok=True)
