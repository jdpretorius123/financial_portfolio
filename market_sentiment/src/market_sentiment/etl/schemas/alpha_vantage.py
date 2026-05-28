"""Alpha Vantage API payload contract for ETL.

Contracts:
    TickerSentiment: Contract for an article's ticker sentiment information.
    TopicMention: Contract for an article's mentioned topics.
    FeedItem: Contract for each article in a payload.
    NewsSentimentResponse: Contract for payload.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class TickerSentiment(BaseModel):
    """Contract for an article's ticker sentiment information.

    Stores the ticker, the article relevance score, and the ticker's sentiment score
    and label for each ticker mentioned in an article.

    Attributes:
        ticker (str): The company ticker.
        relevance_score (float): The relevance of the article's message with the
            ticker.
        ticker_sentiment_score (float): The Alpha Vantage sentiment score of the
            article toward the ticker.
        ticker_sentiment_label (Literal[str]): The label for the Alpha Vantage
            ticker_sentiment_score.
    """

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
    """Contract for an article's mentioned topics.

    Stores the topics associated with an article for each article in a payload.

    Attributes:
        topic (str): An article's topic.
        relevance_score (str): The relevance of the topic within an article.
    """

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    topic: str
    relevance_score: float


class FeedItem(BaseModel):
    """Contract for each article in a payload.

    Stores the article's inherent information and associated Alpha Vantage scores.

    Attributes:
        title (str): Article's title.
        url (str): Article's URL.
        time_published (datetime): Datetime when article was published.
        authors (list[str]): Article author(s).
        summary (str): Article summary/description.
        banner_image (str | None): Figure image for the article's webpage.
        source (str): Article's publisher.
        category_within_source (str): Subsection where the article is listed in the
            publisher's periodical.
        source_domain (str): The homepage of the article's source.
        topics (list[TopicMention]): The article's topics.
        overall_sentiment_score (float): The Alpha Vantage sentiment score of the
            article toward the target ticker.
        overall_sentiment_label (Literal[str]): The label for the Alpha Vantage
            overall_sentiment_score.
        ticker_sentiment (list[TickerSentiment]): The ticker sentiment information
            for each ticker mentioned in the article.

    Methods:
        parse_time_published(): Parses a datetime string to keep datetime data type
            intact.
    """

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
    """Contract for payload.

    Stores the complete payload associated with one ticker.

    Attributes:
        items (int): The number of items in the payload.
        sentiment_score_definition (str): The definition of Alpha Vantage's sentiment
            score.
        relevance_score_definition (str): The definition of Alpha Vantage's relevance
            score.
        feed (list[FeedItem]): The individual articles in the payload for one ticker.
    """

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    items: int
    sentiment_score_definition: str
    relevance_score_definition: str
    feed: list[FeedItem]
