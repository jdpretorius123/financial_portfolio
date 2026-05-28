"""NewsAPI payload contract for ETL.

Contracts:
    Source: Contract for article publisher information.
    Article: Contract for each article in a payload.
    EverythingResponse: Contract for a payload.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    """Contract for article publisher information.

    Attributes:
        id (str | None): The ID of the article's publisher.
        name (str | None): The name of the article's publisher.
    """

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    id: str | None = None
    name: str | None = None


class Article(BaseModel):
    """Contract for each article in a payload.

    Attributes:
        source (Source): Article's publisher information (ID and name).
        author (str | None): Comma-delimited string of article author(s).
        title (str): Article title.
        description (str | None): Article's description/summary.
        url (str): Article's URL.
        url_to_image (str | None): Figure image for the article's webpage.
        published_at (datetime): Datetime when article was published.
        content (str | None): Short, unedited section from the article.
    """

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    source: Source
    author: str | None = None
    title: str
    description: str | None = None
    url: str
    url_to_image: str | None = Field(default=None, alias="urlToImage")
    published_at: datetime = Field(alias="publishedAt")
    content: str | None = None


class EverythingResponse(BaseModel):
    """Contract for payload.

    Attributes:
        status (Literal[str]): Indicator of API response success.
        total_results (int): The number of items in the payload.
        articles (list[Article]): The individual articles in the payload for one ticker.
    """

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    status: Literal["ok", "error"]
    total_results: int = Field(alias="totalResults")
    articles: list[Article]
