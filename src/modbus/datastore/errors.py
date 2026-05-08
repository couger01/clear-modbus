class DataStoreError(Exception):
    """Base error for datastore address/range/access failures."""


class InvalidAddressError(DataStoreError):
    address: int
    count: int

    def __init__(self, address: int, count: int = 1) -> None:
        self.address = address
        self.count = count
        super().__init__("Invalid address.")


class InvalidValueError(DataStoreError):
    value: object

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__("Invalid value.")


class ReadOnlyDataBlockError(DataStoreError):
    address: int

    def __init__(self, address: int) -> None:
        self.address = address
        super().__init__("Read only data access.")
