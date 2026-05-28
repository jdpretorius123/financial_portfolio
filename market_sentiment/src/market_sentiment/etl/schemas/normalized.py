"""Pydantic models for validating row shape before uploading to BigQuery.

Contracts:

"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from market_sentiment.etl.schemas.alpha_vantage import TopicMention


class NormalizedRow(BaseModel):
    """Contract for row in BigQuery.

    Normalizes the differences in data between the providers (Alpha Vantage
    and NewsAPI) to facilitate upload into BigQuery

    Attributes:
        provider (Literal["alpha_vantage", "newsapi"]): Where the data originated.
        ticker (str): The ticker associated with the data.
        fetch_date (str): Date (YYYY_MM_DD) of the API call to the provider.
        published_at (str): Datetime when the article was published.
        title (str): Article title.
        text (str): Consolidated article text (title and description) for VADER scoring.
        url (str): Article URL.
        source_name (str): Article's publisher.
        authors (list[str]): Article's author(s).
        ticker_sentiment_score (float | None): The Alpha Vantage sentiment score of the
            article toward the ticker.
        ticker_sentiment_label (Literal["Bearish", "Somewhat-Bearish", "Neutral",
            "Somewhat-Bullish", "Bullish"] | None): The label for the Alpha Vantage
            ticker_sentiment_score.
        topics (list[TopicMention]): The article's topics.
        vader_compound (float): The overall sentiment of the text used for scoring.
        vader_pos (float): Ratio of positive text to total text.
        vader_neu (float): Ratio of neutral text to total text.
        vader_neg (float): Ratio of negative text to total text.
    """

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    provider: Literal["alpha_vantage", "newsapi"]
    ticker: str
    fetch_date: str
    published_at: str
    title: str
    text: str
    url: str
    source_name: str | None = None
    authors: list[str]
    ticker_sentiment_score: float | None = None
    ticker_sentiment_label: (
        Literal["Bearish", "Somewhat-Bearish", "Neutral", "Somewhat-Bullish", "Bullish"]
        | None
    ) = None
    topics: list[TopicMention]
    vader_compound: float
    vader_pos: float
    vader_neu: float
    vader_neg: float

    @field_validator("published_at", mode="before")
    @classmethod
    def parse_published_at(cls, value: str) -> str:
        """Parses a datetime to confirm contract with string format."""
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        """Validates a ticker str to confirm expected ticker."""
        if not value:
            raise ValueError("An empty string is not a valid ticker.")
        return value
