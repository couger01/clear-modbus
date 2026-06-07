"""Datastore exception types."""


class DataStoreError(Exception):
    """Base error for datastore address/range/access failures."""


class InvalidAddressError(DataStoreError):
    """Error raised when a datastore range is not mapped.

    Parameters
    ----------
    address : int
        First requested Modbus address.
    count : int, optional
        Number of requested values.

    Attributes
    ----------
    address : int
        First requested Modbus address.
    count : int
        Number of requested values.

    """

    address: int
    count: int

    def __init__(self, address: int, count: int = 1) -> None:
        self.address = address
        self.count = count
        super().__init__("Invalid address.")


class InvalidValueError(DataStoreError):
    """Error raised when a datastore value has an invalid type or range.

    Parameters
    ----------
    value : object
        Invalid value passed to the datastore.

    Attributes
    ----------
    value : object
        Invalid value passed to the datastore.

    """

    value: object

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__("Invalid value.")


class ReadOnlyDataBlockError(DataStoreError):
    """Error raised when writing to a read-only datastore block.

    Parameters
    ----------
    address : int
        First address attempted for the write.

    Attributes
    ----------
    address : int
        First address attempted for the write.

    """

    address: int

    def __init__(self, address: int) -> None:
        self.address = address
        super().__init__("Read only data access.")
