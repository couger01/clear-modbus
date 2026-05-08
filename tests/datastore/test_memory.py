import pytest

from modbus.datastore.blocks import BitBlock, RegisterBlock
from modbus.datastore.errors import InvalidAddressError
from modbus.datastore.memory import MemoryDataStore


def test_memory_datastore_initializes_empty_blocks_by_default() -> None:
    datastore = MemoryDataStore()

    assert datastore.holding_registers == []
    assert datastore.input_registers == []
    assert datastore.coils == []
    assert datastore.discrete_inputs == []


def test_get_holding_registers_reads_from_matching_block() -> None:
    datastore = MemoryDataStore(
        holding_registers=[
            RegisterBlock(start_address=0, values=[1, 2]),
            RegisterBlock(start_address=100, values=[10, 20, 30]),
        ]
    )

    assert datastore.get_holding_registers(address=101, count=2) == [20, 30]


def test_set_holding_registers_writes_to_matching_block() -> None:
    block = RegisterBlock(start_address=100, values=[10, 20, 30])
    datastore = MemoryDataStore(holding_registers=[block])

    datastore.set_holding_registers(address=101, values=[55, 66])

    assert block.values == [10, 55, 66]


def test_get_input_registers_reads_from_matching_block() -> None:
    datastore = MemoryDataStore(
        input_registers=[
            RegisterBlock(start_address=0, values=[1, 2]),
            RegisterBlock(start_address=300, values=[100, 200, 300]),
        ]
    )

    assert datastore.get_input_registers(address=301, count=2) == [200, 300]


def test_get_and_set_coils_use_coil_blocks() -> None:
    block = BitBlock(start_address=10, values=[True, False, True])
    datastore = MemoryDataStore(coils=[block])

    assert datastore.get_coils(address=11, count=2) == [False, True]

    datastore.set_coils(address=11, values=[True, True])

    assert block.values == [True, True, True]


def test_get_discrete_inputs_reads_from_matching_block() -> None:
    datastore = MemoryDataStore(
        discrete_inputs=[
            BitBlock(start_address=0, values=[False]),
            BitBlock(start_address=20, values=[True, False, True]),
        ]
    )

    assert datastore.get_discrete_inputs(address=21, count=2) == [False, True]


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("get_holding_registers", (99, 1)),
        ("set_holding_registers", (99, [1])),
        ("get_input_registers", (99, 1)),
        ("get_coils", (99, 1)),
        ("set_coils", (99, [True])),
        ("get_discrete_inputs", (99, 1)),
    ],
)
def test_memory_datastore_raises_for_unmapped_range(
    method_name: str,
    args: tuple[object, ...],
) -> None:
    datastore = MemoryDataStore(
        holding_registers=[RegisterBlock(start_address=0, values=[1])],
        input_registers=[RegisterBlock(start_address=0, values=[1])],
        coils=[BitBlock(start_address=0, values=[True])],
        discrete_inputs=[BitBlock(start_address=0, values=[True])],
    )
    method = getattr(datastore, method_name)

    with pytest.raises(InvalidAddressError):
        method(*args)
