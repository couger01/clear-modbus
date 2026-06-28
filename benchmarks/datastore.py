"""Datastore microbenchmarks for clear-modbus."""

from __future__ import annotations

import pyperf

from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock

BLOCK_COUNT = 256
BLOCK_SIZE = 16
LAST_BLOCK_ADDRESS = (BLOCK_COUNT - 1) * BLOCK_SIZE

SINGLE_REGISTER_BLOCK = RegisterBlock(
    start_address=0,
    values=list(range(1024)),
)
SINGLE_BIT_BLOCK = BitBlock(
    start_address=0,
    values=[index % 3 == 0 for index in range(2048)],
)
SINGLE_BLOCK_DATASTORE = MemoryDataStore(
    holding_registers=[SINGLE_REGISTER_BLOCK],
    coils=[SINGLE_BIT_BLOCK],
)

MANY_REGISTER_BLOCKS = [
    RegisterBlock(
        start_address=index * BLOCK_SIZE,
        values=list(range(BLOCK_SIZE)),
    )
    for index in range(BLOCK_COUNT)
]
MANY_BIT_BLOCKS = [
    BitBlock(
        start_address=index * BLOCK_SIZE,
        values=[value % 2 == 0 for value in range(BLOCK_SIZE)],
    )
    for index in range(BLOCK_COUNT)
]
MANY_BLOCK_DATASTORE = MemoryDataStore(
    holding_registers=MANY_REGISTER_BLOCKS,
    coils=MANY_BIT_BLOCKS,
)

REGISTER_WRITE_VALUES = [111, 222, 333, 444]
COIL_WRITE_VALUES = [True, False, True, False, True, False, True, False]


def _bench_single_block_register_read() -> list[int]:
    return SINGLE_BLOCK_DATASTORE.get_holding_registers(address=100, count=16)


def _bench_single_block_register_write() -> None:
    SINGLE_BLOCK_DATASTORE.set_holding_registers(
        address=100,
        values=REGISTER_WRITE_VALUES,
    )


def _bench_single_block_coil_read() -> list[bool]:
    return SINGLE_BLOCK_DATASTORE.get_coils(address=100, count=64)


def _bench_single_block_coil_write() -> None:
    SINGLE_BLOCK_DATASTORE.set_coils(address=100, values=COIL_WRITE_VALUES)


def _bench_many_blocks_register_read_first() -> list[int]:
    return MANY_BLOCK_DATASTORE.get_holding_registers(address=0, count=4)


def _bench_many_blocks_register_read_last() -> list[int]:
    return MANY_BLOCK_DATASTORE.get_holding_registers(
        address=LAST_BLOCK_ADDRESS,
        count=4,
    )


def _bench_many_blocks_register_write_last() -> None:
    MANY_BLOCK_DATASTORE.set_holding_registers(
        address=LAST_BLOCK_ADDRESS,
        values=REGISTER_WRITE_VALUES,
    )


def _bench_many_blocks_coil_read_last() -> list[bool]:
    return MANY_BLOCK_DATASTORE.get_coils(address=LAST_BLOCK_ADDRESS, count=8)


def _bench_many_blocks_coil_write_last() -> None:
    MANY_BLOCK_DATASTORE.set_coils(
        address=LAST_BLOCK_ADDRESS,
        values=COIL_WRITE_VALUES,
    )


def _bench_many_blocks_datastore_init() -> MemoryDataStore:
    register_blocks = [
        RegisterBlock(
            start_address=index * BLOCK_SIZE,
            values=list(range(BLOCK_SIZE)),
        )
        for index in range(BLOCK_COUNT)
    ]
    bit_blocks = [
        BitBlock(
            start_address=index * BLOCK_SIZE,
            values=[value % 2 == 0 for value in range(BLOCK_SIZE)],
        )
        for index in range(BLOCK_COUNT)
    ]
    return MemoryDataStore(holding_registers=register_blocks, coils=bit_blocks)


def _main() -> None:
    runner = pyperf.Runner()
    runner.bench_func(
        "datastore_single_block_register_read",
        _bench_single_block_register_read,
    )
    runner.bench_func(
        "datastore_single_block_register_write",
        _bench_single_block_register_write,
    )
    runner.bench_func("datastore_single_block_coil_read", _bench_single_block_coil_read)
    runner.bench_func(
        "datastore_single_block_coil_write",
        _bench_single_block_coil_write,
    )
    runner.bench_func(
        "datastore_many_blocks_register_read_first",
        _bench_many_blocks_register_read_first,
    )
    runner.bench_func(
        "datastore_many_blocks_register_read_last",
        _bench_many_blocks_register_read_last,
    )
    runner.bench_func(
        "datastore_many_blocks_register_write_last",
        _bench_many_blocks_register_write_last,
    )
    runner.bench_func(
        "datastore_many_blocks_coil_read_last",
        _bench_many_blocks_coil_read_last,
    )
    runner.bench_func(
        "datastore_many_blocks_coil_write_last",
        _bench_many_blocks_coil_write_last,
    )
    runner.bench_func("datastore_many_blocks_init", _bench_many_blocks_datastore_init)


if __name__ == "__main__":
    _main()
