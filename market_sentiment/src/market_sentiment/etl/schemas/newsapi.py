"""NewsAPI schema setup."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    """Source class."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    id: str | None = None
    name: str | None = None


class Article(BaseModel):
    """Article class."""

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
    """EverythingResponse class."""

    model_config = ConfigDict(
        frozen=True, str_strip_whitespace=True, extra="ignore", populate_by_name=True
    )

    status: Literal["ok", "error"]
    total_results: int = Field(alias="totalResults")
    articles: list[Article]
