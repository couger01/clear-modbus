"""Server microbenchmarks for clear-modbus."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

import pyperf

from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock
from clear_modbus.protocol.mbap import ModbusTCPFrame
from clear_modbus.protocol.pdu import (
    ReadCoilsRequest,
    ReadHoldingRegistersRequest,
    WriteMultipleCoilsRequest,
    WriteMultipleRegistersRequest,
    WriteSingleCoilRequest,
    WriteSingleRegisterRequest,
)
from clear_modbus.server import ModbusTcpServer

HOLDING_REGISTERS = RegisterBlock(start_address=0, values=list(range(1024)))
COILS = BitBlock(start_address=0, values=[index % 3 == 0 for index in range(2048)])
DATASTORE = MemoryDataStore(holding_registers=[HOLDING_REGISTERS], coils=[COILS])
SERVER = ModbusTcpServer(datastore=DATASTORE)
LOOP = asyncio.new_event_loop()

READ_HOLDING_REQUEST = ReadHoldingRegistersRequest(address=100, count=32)
READ_COILS_REQUEST = ReadCoilsRequest(address=100, count=64)
WRITE_SINGLE_REGISTER_REQUEST = WriteSingleRegisterRequest(address=100, value=1234)
WRITE_SINGLE_COIL_REQUEST = WriteSingleCoilRequest(address=100, value=True)
WRITE_MULTIPLE_REGISTERS_REQUEST = WriteMultipleRegistersRequest(
    address=100,
    values=[111, 222, 333, 444, 555, 666, 777, 888],
)
WRITE_MULTIPLE_COILS_REQUEST = WriteMultipleCoilsRequest(
    address=100,
    values=[True, False, True, False, True, False, True, False],
)

READ_HOLDING_FRAME = ModbusTCPFrame(
    transaction_id=1,
    unit_id=1,
    pdu=READ_HOLDING_REQUEST.encode(),
).encode()


class FakeStreamReader:
    """Stream reader backed by pre-sized chunks."""

    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def readexactly(self, size: int) -> bytes:
        """Return the next chunk if it matches the requested size.

        Returns
        -------
        bytes
            Next chunk from the fake stream.

        Raises
        ------
        asyncio.IncompleteReadError
            If no chunk is available or the chunk size is wrong.

        """
        if not self.chunks:
            raise asyncio.IncompleteReadError(partial=b"", expected=size)
        chunk = self.chunks.pop(0)
        if len(chunk) != size:
            raise asyncio.IncompleteReadError(partial=chunk, expected=size)
        return chunk


class FakeStreamWriter:
    """Stream writer that stores response bytes in memory."""

    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        """Store response bytes."""
        self.data += data

    async def drain(self) -> None:
        """Match the StreamWriter drain API."""
        pass

    def close(self) -> None:
        """Match the StreamWriter close API."""
        pass

    async def wait_closed(self) -> None:
        """Match the StreamWriter wait_closed API."""
        pass


def _run(coro: Awaitable[Any]) -> object:
    return LOOP.run_until_complete(coro)


def _bench_handle_read_holding_registers() -> object:
    return _run(SERVER.handle_request(READ_HOLDING_REQUEST))


def _bench_handle_read_coils() -> object:
    return _run(SERVER.handle_request(READ_COILS_REQUEST))


def _bench_handle_write_single_register() -> object:
    return _run(SERVER.handle_request(WRITE_SINGLE_REGISTER_REQUEST))


def _bench_handle_write_single_coil() -> object:
    return _run(SERVER.handle_request(WRITE_SINGLE_COIL_REQUEST))


def _bench_handle_write_multiple_registers() -> object:
    return _run(SERVER.handle_request(WRITE_MULTIPLE_REGISTERS_REQUEST))


def _bench_handle_write_multiple_coils() -> object:
    return _run(SERVER.handle_request(WRITE_MULTIPLE_COILS_REQUEST))


def _bench_handle_tcp_frame_read_holding_registers() -> bytes:
    reader = FakeStreamReader([READ_HOLDING_FRAME[:7], READ_HOLDING_FRAME[7:]])
    writer = FakeStreamWriter()
    _run(SERVER._handle_client(reader, writer))
    return bytes(writer.data)


def _main() -> None:
    runner = pyperf.Runner()
    runner.bench_func(
        "server_handle_read_holding_registers",
        _bench_handle_read_holding_registers,
    )
    runner.bench_func("server_handle_read_coils", _bench_handle_read_coils)
    runner.bench_func(
        "server_handle_write_single_register",
        _bench_handle_write_single_register,
    )
    runner.bench_func(
        "server_handle_write_single_coil",
        _bench_handle_write_single_coil,
    )
    runner.bench_func(
        "server_handle_write_multiple_registers",
        _bench_handle_write_multiple_registers,
    )
    runner.bench_func(
        "server_handle_write_multiple_coils",
        _bench_handle_write_multiple_coils,
    )
    runner.bench_func(
        "server_tcp_frame_read_holding_registers",
        _bench_handle_tcp_frame_read_holding_registers,
    )
    LOOP.close()


if __name__ == "__main__":
    _main()
