"""Alpha Vantage schema setup."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class TickerSentiment(BaseModel):
    """TickerSentiment class."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    ticker: str
    relevance_score: float
    ticker_sentiment_score: float
    ticker_sentiment_label: Literal[
        "Bearish", "Somewhat-Bearish", "Neutral", "Somewhat-Bullish", "Bullish"
    ]


class TopicMention(BaseModel):
    """TopicMention class."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    topic: str
    relevance_score: float


class FeedItem(BaseModel):
    """FeedItem class."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    title: str
    url: str
    time_published: datetime
    authors: list[str]
    summary: str
    banner_image: str | None = None
    source: str
    category_within_source: str
    source_domain: str
    topics: list[TopicMention]
    overall_sentiment_score: float
    overall_sentiment_label: Literal[
        "Bearish", "Somewhat-Bearish", "Neutral", "Somewhat-Bullish", "Bullish"
    ]
    ticker_sentiment: list[TickerSentiment]

    @field_validator("time_published", mode="before")
    @classmethod
    def parse_time_published(cls, value: str) -> datetime:
        """Parses a datetime string to keep datetime data type intact."""
        return datetime.strptime(value, "%Y%m%dT%H%M%S")


class NewsSentimentResponse(BaseModel):
    """NewsSentiment Response class."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    items: int
    sentiment_score_definition: str
    relevance_score_definition: str
    feed: list[FeedItem]
