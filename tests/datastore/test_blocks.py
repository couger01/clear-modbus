import pytest

from modbus.datastore.blocks import BitBlock, RegisterBlock
from modbus.datastore.errors import (
    InvalidAddressError,
    InvalidValueError,
    ReadOnlyDataBlockError,
)


def test_register_block_end_address_is_inclusive() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    assert block.end_address == 102


def test_register_block_contains_full_range() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    assert block.contains(100) is True
    assert block.contains(101, 2) is True
    assert block.contains(99) is False
    assert block.contains(102, 2) is False
    assert block.contains(100, 0) is False


def test_register_block_read_returns_copy_of_requested_values() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    values = block.read(address=101, count=2)

    assert values == [20, 30]

    values[0] = 999

    assert block.values == [10, 20, 30]


def test_register_block_read_rejects_unmapped_range() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    with pytest.raises(InvalidAddressError):
        block.read(address=99, count=1)

    with pytest.raises(InvalidAddressError):
        block.read(address=102, count=2)


def test_register_block_write_updates_values() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    block.write(address=101, values=[55, 66])

    assert block.values == [10, 55, 66]


def test_register_block_write_rejects_invalid_values_without_mutating() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    with pytest.raises(InvalidValueError):
        block.write(address=101, values=[55, 0x10000])

    assert block.values == [10, 20, 30]


def test_register_block_write_rejects_non_int_values_without_mutating() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])

    with pytest.raises(InvalidValueError):
        block.write(address=101, values=[55, True])

    with pytest.raises(InvalidValueError):
        block.write(address=101, values=[55, "66"])

    assert block.values == [10, 20, 30]


def test_register_block_rejects_readonly_write() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30], readonly=True)

    with pytest.raises(ReadOnlyDataBlockError):
        block.write(address=101, values=[55])

    assert block.values == [10, 20, 30]


def test_bit_block_contains_reads_and_writes_bits() -> None:
    block = BitBlock(start_address=0, values=[True, False, True])

    assert block.end_address == 2
    assert block.contains(0) is True
    assert block.contains(1, 2) is True
    assert block.contains(2, 2) is False

    values = block.read(address=1, count=2)

    assert values == [False, True]

    values[0] = True

    assert block.values == [True, False, True]

    block.write(address=1, values=[True, True])

    assert block.values == [True, True, True]


def test_bit_block_write_rejects_invalid_values_without_mutating() -> None:
    block = BitBlock(start_address=0, values=[True, False, True])

    with pytest.raises(InvalidValueError):
        block.write(address=1, values=[True, 1])

    assert block.values == [True, False, True]


def test_bit_block_rejects_readonly_write() -> None:
    block = BitBlock(start_address=0, values=[True, False, True], readonly=True)

    with pytest.raises(ReadOnlyDataBlockError):
        block.write(address=1, values=[True])

    assert block.values == [True, False, True]
