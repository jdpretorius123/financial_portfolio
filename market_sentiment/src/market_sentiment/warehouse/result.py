"""Read classes for transferring read response data from warehousing to ETL.

Read is the parent class of ReadResult and ReadFailure. ReadResult and ReadFailure
transfer raw read response data from warehousing (R2) to ETL. The ReadResult class is
used for transferring successful read responses, and the ReadFailure class is used for
transferring failed read responses.

Classes:
    Read: Parent class of ReadResult and ReadFailure data.
    ReadResult: Transfers successful read responses from warehousing to ETL.
    ReadFailure: Transfers unsuccessful read responses from warehousing to ETL.
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime

from market_sentiment.warehouse._helpers import DATA_DESC_BY_SOURCE


class FileTypeError(Exception):
    """Custom exception for an invalid file type in a warehousing key."""

    pass


class Read(ABC):
    """Parent class of ReadResult and ReadFailure.

    Attributes:
        read_date (str): The date of the read.
    """

    def __init__(self, read_date: str) -> None:
        """Initializes the Read class.

        Args:
            read_date (str): The date of the read.

        Raises:
            ValueError: If an incorrect value is passed to a setter.
        """
        self.read_date = read_date

    @property
    def read_date(self) -> str:
        """The date (YYYY_MM_DD) of the read."""
        return self._read_date

    @read_date.setter
    def read_date(self, value: str) -> None:
        datetime.strptime(value, "%Y_%m_%d")
        self._read_date = value

    @property
    @abstractmethod
    def key(self) -> str:
        """The object's warehousing key."""
        pass

    @property
    @abstractmethod
    def upload_metadata(self) -> dict[str, str] | None:
        """The metadata uploaded into the warehouse with the object."""
        pass


class ReadResult(Read):
    """Transfers successful read data from warehousing to ETL.

    The ReadResult class transfers usable read data from warehousing to ETL.

    Attributes:
        key (str): The object's warehousing key.
        upload_metadata (dict[str, str]): The metadata uploaded into the warehouse with
            the object.
        usable_data (bytes): Usable data from the warehouse.
    """

    def __init__(
        self,
        read_date: str,
        key: str,
        upload_metadata: dict[str, str],
        usable_data: bytes,
    ):
        """Initializes the ReadResult class.

        Args:
            read_date (str): The date of the read.
            key (str): The object's warehousing key.
            upload_metadata (dict[str, str]): The metadata uploaded into the
                warehouse with the object.
            usable_data (bytes): Usable data from the warehouse.

        Raises:
            KeyError: If a key is missing from upload_metadata.
            ValueError: If None is incorrectly passed to the upload_metadata
                setter.
            FileTypeError: If setting an invalid file type as a warehousing key.
        """
        super().__init__(read_date)
        self.key = key
        self.upload_metadata = upload_metadata
        self.usable_data = usable_data

    @property
    def key(self) -> str:
        """The object's warehousing key."""
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        expected_length = 4
        key_parts = value.split("/")
        if len(key_parts) != expected_length:
            err_msg = f"Invalid Key <source>/<ticker>/<fetch_date>/<data_desc>: {value}"
            raise ValueError(err_msg)

        source = key_parts[0]
        ticker = key_parts[1]
        fetch_date = key_parts[2]
        data_desc, file_type = os.path.splitext(key_parts[3])

        if source not in DATA_DESC_BY_SOURCE.keys():
            raise ValueError("Valid Sources: AlphaVantage, NewsAPI.")

        if ticker == "":
            raise ValueError("Missing Ticker.")

        datetime.strptime(fetch_date, "%Y_%m_%d")

        if data_desc not in DATA_DESC_BY_SOURCE.values():
            raise ValueError("Valid Data Descriptions: news_sentiment and articles.")

        if file_type != ".json":
            raise FileTypeError("Valid File Types: .json")

        self._key = value

    @property
    def upload_metadata(self) -> dict[str, str]:
        """The metadata uploaded into the warehouse with the object."""
        return self._upload_metadata

    @upload_metadata.setter
    def upload_metadata(self, value: dict[str, str] | None) -> None:
        if value is None:
            raise ValueError("Metadata cannot be None for a successful ReadResult.")

        expected_keys = {"fetch_date", "source", "ticker", "http_status"}
        missing_keys = expected_keys - value.keys()
        if missing_keys:
            raise KeyError(f"Missing Keys: {missing_keys}.")
        self._upload_metadata = value

    @property
    def usable_data(self) -> bytes:
        """Usable data from the warehouse."""
        return self._usable_data

    @usable_data.setter
    def usable_data(self, value: bytes) -> None:
        if isinstance(value, bytes):
            self._usable_data = value
        else:
            raise TypeError("Usable data are bytes from the warehousing streamingbody.")


class ReadFailure(Read):
    """Transfers unsuccessful read information from warehousing to ETL.

    The ReadFailure class transfers unsuccessful read information from
    warehousing to ETL.

    Attributes:
        key (str): The object's warehousing key.
        upload_metadata (dict[str, str] | None): The metadata uploaded into the
                warehouse with the object.
        error_message (str): Description of the read response error.
        error_type (str): The error type of the read response.
    """

    def __init__(
        self,
        read_date: str,
        key: str,
        upload_metadata: dict[str, str] | None,
        error_message: str,
        error_type: str,
    ):
        """Initializes the ReadFailure class.

        Args:
            read_date (str): The date of the read.
            key (str): The object's warehousing key.
            upload_metadata (dict[str, str] | None): The metadata uploaded into the
                warehouse with the object.
            error_message (str): A description of the read response error.
            error_type (str): The error type of the read response.
        """
        super().__init__(read_date)
        self.key = key
        self.upload_metadata = upload_metadata
        self.error_message = error_message
        self.error_type = error_type

    @property
    def key(self) -> str:
        """The object's warehousing key."""
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        expected_length = 1
        key_parts = value.split("/")
        source = key_parts[0]

        if len(key_parts) != expected_length:
            err_msg = f"Invalid Key <source>/: {value}"
            raise ValueError(err_msg)

        if source not in DATA_DESC_BY_SOURCE.keys():
            raise ValueError("Valid Sources: AlphaVantage, NewsAPI.")

        self._key = value

    @property
    def upload_metadata(self) -> dict[str, str] | None:
        """The metadata uploaded into the warehouse with the object."""
        return self._upload_metadata

    @upload_metadata.setter
    def upload_metadata(self, value: dict[str, str] | None) -> None:
        expected_keys = {"fetch_date", "source", "ticker", "http_status"}
        if value is not None:
            missing_keys = expected_keys - value.keys()
            if missing_keys:
                raise KeyError(f"Missing Keys: {missing_keys}.")
        self._upload_metadata = value

    @property
    def error_message(self) -> str:
        """Description of the read response error."""
        return self._error_message

    @error_message.setter
    def error_message(self, value: str) -> None:
        self._error_message = value

    @property
    def error_type(self) -> str:
        """The error type of the read response."""
        return self._error_type

    @error_type.setter
    def error_type(self, value: str) -> None:
        self._error_type = value
