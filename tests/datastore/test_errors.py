from modbus.datastore.errors import InvalidAddressError, InvalidValueError, ReadOnlyDataBlockError


def test_invalid_address_error_stores_address_and_count() -> None:
    error = InvalidAddressError(address=10, count=3)

    assert error.address == 10
    assert error.count == 3
    assert "Invalid address" in str(error)


def test_invalid_value_error_stores_value() -> None:
    error = InvalidValueError(value=0x10000)

    assert error.value == 0x10000
    assert "Invalid value" in str(error)


def test_readonly_data_block_error_stores_address() -> None:
    error = ReadOnlyDataBlockError(address=5)

    assert error.address == 5
    assert "Read only data access" in str(error)
