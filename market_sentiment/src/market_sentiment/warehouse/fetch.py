"""Transfer classes for moving raw API response data from acquisition to warehousing.

The Fetch, FetchResult, and FetchFailure classes pass raw API response data from
acquisition to warehousing. The FetchResult class is used for transferring
successful API responses, and the FetchFailure class is used for transferring
failed API responses.

Classes:
    Fetch: Parent class of FetchResult and FetchFailure.
    FetchResult: Transfers successful API responses from acquisition to warehousing.
    FetchFailure: Transfers unsuccessful API responses from acquisition to warehousing.
"""

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit


class URLSchemeError(Exception):
    """Custom exception for invalid URL scheme."""

    pass


class URLNetlocError(Exception):
    """Custom exception for invalid URL netloc."""

    pass


class URLPathError(Exception):
    """Custom exception for invalid URL path."""

    pass


class Fetch:
    """Transfers API response data from acquisition to warehousing.

    Attributes:
        fetch_date (str): The date of the API call.
        source (str): The website that hosts the API.
        ticker (str): The ticker of the tech company of interest.
        http_status (str): The status of the API response.
    """

    def __init__(self, fetch_date: str, source: str, ticker: str, http_status: str):
        """Initializes the Fetch class.

        Args:
            fetch_date (str): The date of the API call.
            source (str): The website that hosts the API.
            ticker (str): The ticker of the tech company of interest.
            http_status (str): The status of the API response.

        Raises:
            ValueError: If an incorrect value is passed to a setter.
        """
        self.fetch_date = fetch_date
        self.source = source
        self.ticker = ticker
        self.http_status = http_status

    @property
    def fetch_date(self) -> str:
        """The date (YYYY_MM_DD) of the API call."""
        return self._fetch_date

    @fetch_date.setter
    def fetch_date(self, value: str) -> None:
        self._fetch_date = datetime.strptime(value, "%Y_%m_%d").strftime("%Y_%m_%d")

    @property
    def source(self) -> str:
        """The website that hosts the API."""
        return self._source

    @source.setter
    def source(self, value: str) -> None:
        valid_api = ("AlphaVantage", "NewsAPI")
        if value not in valid_api:
            raise ValueError("Source must be either AlphaVantage or NewsAPI.")
        self._source = value

    @property
    def ticker(self) -> str:
        """The ticker of the tech company of interest."""
        return self._ticker

    @ticker.setter
    def ticker(self, value: str) -> None:
        self._ticker = value

    @property
    def http_status(self) -> str:
        """The status of the API response."""
        return self._http_status

    @http_status.setter
    def http_status(self, value: str) -> None:
        self._http_status = value


class FetchResult(Fetch):
    """Transfers successful API response data from acquisition to warehousing.

    The FetchResult class transfers usable API response data from
    acquisition to warehousing.

    Attributes:
        endpoint_url (str): The network connection point of the API.
        usable_data (Any): Usable data from the API response.
    """

    def __init__(
        self,
        fetch_date: str,
        source: str,
        ticker: str,
        http_status: str,
        endpoint_url: str,
        usable_data: Any,
    ):
        """Initializes the FetchResult class.

        Args:
            fetch_date (str): The date of the API call.
            source (str): The website that hosts the API.
            ticker (str): The ticker for the tech company of interest.
            http_status (str): The status of the API response.
            endpoint_url (str): The network connection point of the API.
            usable_data (Any): Usable data from the API response.

        Raises:
            ValueError: If an incorrect value is passed to a setter.
            URLSchemeError: If an Endpoint URL lacks a scheme.
            URLNetlocError: If an Endpoint URL lacks a netloc component.
            URLPathError: If an Endpoint URL lacks a path component.
        """
        super().__init__(fetch_date, source, ticker, http_status)
        self.endpoint_url = endpoint_url
        self.usable_data = usable_data

    @property
    def endpoint_url(self) -> str:
        """The network connection point of the API."""
        return self._endpoint_url

    @endpoint_url.setter
    def endpoint_url(self, value: str) -> None:
        valid_scheme = ("https", "http")
        parts = urlsplit(value)

        if parts.scheme not in valid_scheme:
            raise URLSchemeError("Invalid Endpoint URL scheme.")

        if not parts.netloc:
            raise URLNetlocError("Invalid Endpoint URL netloc.")

        if not parts.path:
            raise URLPathError("Invalid Endpoint URL path.")

        self._endpoint_url = value

    @property
    def usable_data(self) -> Any:
        """Usable data from the API response."""
        return self._usable_data

    @usable_data.setter
    def usable_data(self, value: Any) -> None:
        self._usable_data = value


class FetchFailure(Fetch):
    """Transfers unsuccessful API response data from acquisition to warehousing.

    The FetchFailure class transfers unsuccessful API response data from
    acquisition to warehousing.

    Attributes:
        error_message (str): Description of the API response error.
        error_type (str): The error type of the API response.
        unusable_data (Any | None): Unusable data from the API response.
    """

    def __init__(
        self,
        fetch_date: str,
        source: str,
        ticker: str,
        http_status: str,
        error_message: str,
        error_type: str,
        unusable_data: Any | None,
    ):
        """Initializes the FetchFailure class.

        Args:
            fetch_date (str): The date of the API call.
            source (str): The website that hosts the API.
            ticker (str): The ticker for the tech company of interest.
            http_status (str): The status of the API response.
            error_message (str): Description of the API response error.
            error_type (str): The error type of the API response.
            unusable_data (Any | None): Unusable data from the API response.
        """
        super().__init__(fetch_date, source, ticker, http_status)
        self.error_message = error_message
        self.error_type = error_type
        self.unusable_data = unusable_data

    @property
    def error_message(self) -> str:
        """Description of the API response error."""
        return self._error_message

    @error_message.setter
    def error_message(self, value: str) -> None:
        self._error_message = value

    @property
    def error_type(self) -> str:
        """The error type of the API response."""
        return self._error_type

    @error_type.setter
    def error_type(self, value: str) -> None:
        self._error_type = value

    @property
    def unusable_data(self) -> Any | None:
        """Unusable data from the API response."""
        return self._unusable_data

    @unusable_data.setter
    def unusable_data(self, value: Any | None) -> None:
        self._unusable_data = value
