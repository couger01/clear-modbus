import asyncio

import pytest

from clear_modbus.constants import DEFAULT_MODBUS_TCP_PORT
from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock
from clear_modbus.datastore.errors import InvalidValueError
from clear_modbus.protocol.functions import ExceptionCode
from clear_modbus.protocol.mbap import ModbusTCPFrame
from clear_modbus.protocol.pdu import (
    ExceptionResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleCoilsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleCoilRequest,
    WriteSingleCoilResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from clear_modbus.server import ModbusTcpServer


class FakeStreamReader:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def readexactly(self, size: int) -> bytes:
        if not self.chunks:
            raise asyncio.IncompleteReadError(partial=b"", expected=size)

        chunk = self.chunks.pop(0)
        assert len(chunk) == size
        return chunk


class FakeStreamWriter:
    def __init__(self) -> None:
        self.data = bytearray()
        self.drained = False
        self.closed = False
        self.waited_closed = False

    def write(self, data: bytes) -> None:
        self.data += data

    async def drain(self) -> None:
        self.drained = True

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.waited_closed = True


def test_server_initializes_bind_settings_and_datastore() -> None:
    datastore = MemoryDataStore()

    server = ModbusTcpServer(
        host="127.0.0.1",
        port=1502,
        datastore=datastore,
    )

    assert server.host == "127.0.0.1"
    assert server.port == 1502
    assert server.datastore is datastore
    assert server._server is None


def test_server_uses_defaults_when_optional_settings_are_omitted() -> None:
    server = ModbusTcpServer()

    assert server.host == "0.0.0.0"
    assert server.port == DEFAULT_MODBUS_TCP_PORT
    assert isinstance(server.datastore, MemoryDataStore)
    assert server._server is None


@pytest.mark.asyncio
async def test_server_context_manager_starts_and_stops() -> None:
    class TrackingServer(ModbusTcpServer):
        started: bool = False
        stopped: bool = False

        async def start(self) -> None:
            self.started = True

        async def stop(self) -> None:
            self.stopped = True

    server = TrackingServer()

    async with server as active_server:
        assert active_server is server
        assert server.started is True
        assert server.stopped is False

    assert server.stopped is True


@pytest.mark.asyncio
async def test_handle_request_routes_reads_to_datastore() -> None:
    datastore = MemoryDataStore(
        holding_registers=[RegisterBlock(start_address=0, values=[10, 20])],
        input_registers=[RegisterBlock(start_address=100, values=[30, 40])],
        coils=[BitBlock(start_address=200, values=[True, False])],
        discrete_inputs=[BitBlock(start_address=300, values=[False, True])],
    )
    server = ModbusTcpServer(datastore=datastore)

    holding_response = await server.handle_request(
        ReadHoldingRegistersRequest(address=0, count=2)
    )
    input_response = await server.handle_request(
        ReadInputRegistersRequest(address=100, count=2)
    )
    coils_response = await server.handle_request(ReadCoilsRequest(address=200, count=2))
    discrete_inputs_response = await server.handle_request(
        ReadDiscreteInputsRequest(address=300, count=2)
    )

    assert holding_response == ReadRegistersResponse(
        function_code=0x03, values=[10, 20]
    )
    assert input_response == ReadRegistersResponse(function_code=0x04, values=[30, 40])
    assert coils_response == ReadBitsResponse(function_code=0x01, values=[True, False])
    assert discrete_inputs_response == ReadBitsResponse(
        function_code=0x02, values=[False, True]
    )


@pytest.mark.asyncio
async def test_handle_request_routes_writes_to_datastore() -> None:
    holding_registers = RegisterBlock(start_address=0, values=[10, 20, 30])
    coils = BitBlock(start_address=0, values=[False, False, False])
    datastore = MemoryDataStore(holding_registers=[holding_registers], coils=[coils])
    server = ModbusTcpServer(datastore=datastore)

    single_coil_response = await server.handle_request(
        WriteSingleCoilRequest(address=1, value=True)
    )
    single_response = await server.handle_request(
        WriteSingleRegisterRequest(address=1, value=99)
    )
    multiple_coils_response = await server.handle_request(
        WriteMultipleCoilsRequest(address=0, values=[True, False])
    )
    multiple_response = await server.handle_request(
        WriteMultipleRegistersRequest(address=0, values=[55, 66])
    )

    assert single_coil_response == WriteSingleCoilResponse(
        function_code=0x05,
        address=1,
        value=True,
    )
    assert single_response == WriteSingleRegisterResponse(
        function_code=0x06,
        address=1,
        value=99,
    )
    assert multiple_coils_response == WriteMultipleCoilsResponse(
        function_code=0x0F,
        address=0,
        count=2,
    )
    assert multiple_response == WriteMultipleRegistersResponse(
        function_code=0x10,
        address=0,
        count=2,
    )
    assert holding_registers.values == [55, 66, 30]
    assert coils.values == [True, False, False]


@pytest.mark.asyncio
async def test_handle_request_converts_invalid_address_to_exception_response() -> None:
    server = ModbusTcpServer(datastore=MemoryDataStore())

    response = await server.handle_request(
        ReadHoldingRegistersRequest(address=0, count=1)
    )

    assert response == ExceptionResponse(
        function_code=0x03,
        exception_code=ExceptionCode.ILLEGAL_DATA_ADDRESS,
    )


@pytest.mark.asyncio
async def test_handle_request_converts_invalid_value_to_exception_response() -> None:
    class InvalidValueDataStore:
        def get_holding_registers(self, address: int, count: int) -> list[int]:
            raise AssertionError("unexpected read")

        def set_holding_registers(self, address: int, values: list[int]) -> None:
            raise InvalidValueError(values[0])

        def get_input_registers(self, address: int, count: int) -> list[int]:
            raise AssertionError("unexpected read")

        def get_coils(self, address: int, count: int) -> list[bool]:
            raise AssertionError("unexpected read")

        def set_coils(self, address: int, values: list[bool]) -> None:
            raise AssertionError("unexpected write")

        def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
            raise AssertionError("unexpected read")

    server = ModbusTcpServer(datastore=InvalidValueDataStore())

    response = await server.handle_request(
        WriteSingleRegisterRequest(address=0, value=1)
    )

    assert response == ExceptionResponse(
        function_code=0x06,
        exception_code=ExceptionCode.ILLEGAL_DATA_VALUE,
    )


@pytest.mark.asyncio
async def test_handle_request_converts_unsupported_request_to_exception_response() -> (
    None
):
    class UnsupportedRequest:
        function_code = 0x02

        def encode(self) -> bytes:
            return bytes.fromhex("02 00 00 00 01")

    server = ModbusTcpServer()

    response = await server.handle_request(UnsupportedRequest())

    assert response == ExceptionResponse(
        function_code=0x02,
        exception_code=ExceptionCode.ILLEGAL_FUNCTION,
    )


@pytest.mark.asyncio
async def test_handle_client_reads_request_and_writes_response_frame() -> None:
    datastore = MemoryDataStore(
        holding_registers=[RegisterBlock(start_address=0, values=[10, 20])]
    )
    server = ModbusTcpServer(datastore=datastore)
    request_frame = ModbusTCPFrame(
        transaction_id=123,
        unit_id=7,
        pdu=ReadHoldingRegistersRequest(address=0, count=2).encode(),
    ).encode()
    reader = FakeStreamReader(chunks=[request_frame[:7], request_frame[7:]])
    writer = FakeStreamWriter()

    await server._handle_client(reader, writer)

    expected_frame = ModbusTCPFrame(
        transaction_id=123,
        unit_id=7,
        pdu=ReadRegistersResponse(function_code=0x03, values=[10, 20]).encode(),
    ).encode()
    assert bytes(writer.data) == expected_frame
    assert writer.drained is True
    assert writer.closed is True
    assert writer.waited_closed is True


@pytest.mark.asyncio
async def test_handle_client_writes_exception_frame_for_unsupported_function() -> None:
    server = ModbusTcpServer()
    request_frame = ModbusTCPFrame(
        transaction_id=123,
        unit_id=7,
        pdu=bytes.fromhex("11 00 00 00 01"),
    ).encode()
    reader = FakeStreamReader(chunks=[request_frame[:7], request_frame[7:]])
    writer = FakeStreamWriter()

    await server._handle_client(reader, writer)

    expected_frame = ModbusTCPFrame(
        transaction_id=123,
        unit_id=7,
        pdu=ExceptionResponse(
            function_code=0x11,
            exception_code=ExceptionCode.ILLEGAL_FUNCTION,
        ).encode(),
    ).encode()
    assert bytes(writer.data) == expected_frame
    assert writer.closed is True
