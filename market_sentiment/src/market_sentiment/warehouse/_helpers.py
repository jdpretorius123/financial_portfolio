"""Functions to help transfer data.

These functions help transfer data from acquisition to warehousing and
from warehousing to ETL.

Variables:
    DATA_DESC_BY_SOURCE: Dictionary that associates source with data.

Functions:
    get_data_desc(): Get the description of the data given the key.
    create_batch_id(): Create a batch ID for the content uploaded into R2.
    create_warehouse_key(): Create an object warehouse key.
    verify_env(): Verify the existence of a required environment variable.
"""

import os

DATA_DESC_BY_SOURCE = {
    "AlphaVantage": "news_sentiment",
    "NewsAPI": "articles",
}


def get_data_desc(key_prefix: str) -> str:
    """Get the description of the data given the key.

    Args:
        key_prefix (str): The warehousing key prefix of the target data.

    Returns:
        str: The description (news_sentiment or articles) of the data.
    """
    source = key_prefix.split("/", 1)[0]
    return DATA_DESC_BY_SOURCE[source]


def create_batch_id(
    source: str,
    ticker: str,
    fetch_date: str,
    data_desc: str,
) -> str:
    """Create a batch ID for the content uploaded into R2.

    Args:
        source (str): Website that hosts the API.
        ticker (str): Ticker for a tech company.
        fetch_date (str): Date of the API call.
        data_desc (str): Token describing the nature of the data.

    Returns:
        The batch ID (R2 object key) for the content to be uploaded.
    """
    batch_id = f"{source}/{ticker}/{fetch_date}/{data_desc}.json"
    return batch_id


def create_warehouse_key(key_prefix: str, fetch_date: str) -> str:
    """Create an object warehouse key.

    Args:
        key_prefix (str): The warehouse key prefix; <source>/<ticker>/.
        fetch_date (str): The date of initial API transaction

    Returns:
        str: The warehouse key.
    """
    warehouse_key = f"{key_prefix}{fetch_date}/{get_data_desc(key_prefix)}.json"
    return warehouse_key


def verify_env(var_name: str) -> str:
    """Verify the existence of a required environment variable.

    Args:
        var_name: The name of the required environment variable to verify existence.

    Returns:
        str: The value of the required environment variable if successful.

    Raises:
        RuntimeError: If the required environment variable is empty or missing.
    """
    val = os.getenv(var_name)
    if not val:
        raise RuntimeError(f"{var_name} is empty/missing.")
    return val
