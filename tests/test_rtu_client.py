import pytest

from modbus.protocol.pdu import (
    ExceptionResponse,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from modbus.protocol.rtu import ModbusRTUFrame
from modbus.rtu_client import ModbusRtuClient
from modbus.transport import SerialTransport


class FakeTransport:
    def __init__(self, receive_chunks: list[bytes] | None = None) -> None:
        self.receive_chunks = receive_chunks or []
        self.sent: list[bytes] = []
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.closed = True

    async def send(self, data: bytes) -> None:
        self.sent.append(data)

    async def receive(self, size: int) -> bytes:
        if not self.receive_chunks:
            raise AssertionError(f"Unexpected receive ({size})")

        chunk = self.receive_chunks.pop(0)
        assert len(chunk) == size
        return chunk


def split_rtu_response(frame: ModbusRTUFrame) -> list[bytes]:
    data = frame.encode()
    function_code = data[1]
    if function_code & 0x80:
        return [data[:2], data[2:]]
    if function_code in (0x03, 0x04):
        return [data[:2], data[2:3], data[3:]]
    return [data[:2], data[2:]]


def test_rtu_client_initializes_serial_transport_and_codec() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", unit_id=1, baudrate=19200, timeout=2)

    assert client.port == "/dev/ttyUSB0"
    assert client.unit_id == 1
    assert client.baudrate == 19200
    assert client.timeout == 2
    assert isinstance(client.transport, SerialTransport)


@pytest.mark.asyncio
async def test_rtu_client_context_manager_connects_and_closes() -> None:
    transport = FakeTransport()
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    async with client as active_client:
        assert active_client is client
        assert transport.connected is True
        assert transport.closed is False

    assert transport.closed is True


@pytest.mark.asyncio
async def test_execute_sends_encoded_request_and_decodes_read_response() -> None:
    response_frame = ModbusRTUFrame(
        unit_id=1,
        pdu=ReadRegistersResponse(function_code=0x03, values=[10, 20]).encode(),
    )
    transport = FakeTransport(receive_chunks=split_rtu_response(response_frame))
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    request = ReadHoldingRegistersRequest(address=0, count=2)
    response = await client.execute(request)

    assert transport.sent == [bytes.fromhex("01 03 00 00 00 02 C4 0B")]
    assert response == ReadRegistersResponse(function_code=0x03, values=[10, 20])


@pytest.mark.asyncio
async def test_execute_uses_unit_id_override() -> None:
    response_frame = ModbusRTUFrame(
        unit_id=2,
        pdu=ReadRegistersResponse(function_code=0x03, values=[10, 20]).encode(),
    )
    transport = FakeTransport(receive_chunks=split_rtu_response(response_frame))
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    request = ReadHoldingRegistersRequest(address=0, count=2)
    response = await client.execute(request, unit_id=2)

    assert transport.sent == [bytes.fromhex("02 03 00 00 00 02 C4 38")]
    assert isinstance(response, ReadRegistersResponse)


@pytest.mark.asyncio
async def test_execute_decodes_fixed_write_response() -> None:
    response_frame = ModbusRTUFrame(
        unit_id=1,
        pdu=WriteSingleRegisterResponse(
            function_code=0x06,
            address=0,
            value=10,
        ).encode(),
    )
    transport = FakeTransport(receive_chunks=split_rtu_response(response_frame))
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    request = WriteSingleRegisterRequest(address=0, value=10)
    response = await client.execute(request)

    assert response == WriteSingleRegisterResponse(
        function_code=0x06,
        address=0,
        value=10,
    )


@pytest.mark.asyncio
async def test_execute_decodes_exception_response() -> None:
    response_frame = ModbusRTUFrame(
        unit_id=1,
        pdu=ExceptionResponse(function_code=0x03, exception_code=0x02).encode(),
    )
    transport = FakeTransport(receive_chunks=split_rtu_response(response_frame))
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    request = ReadHoldingRegistersRequest(address=0, count=2)
    response = await client.execute(request)

    assert response == ExceptionResponse(function_code=0x03, exception_code=0x02)


@pytest.mark.asyncio
async def test_execute_rejects_bad_crc() -> None:
    response = ModbusRTUFrame(
        unit_id=1,
        pdu=ReadRegistersResponse(function_code=0x03, values=[10, 20]).encode(),
    ).encode()
    bad_response = response[:-1] + b"\x00"
    transport = FakeTransport(
        receive_chunks=[bad_response[:2], bad_response[2:3], bad_response[3:]]
    )
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    with pytest.raises(ValueError):
        await client.execute(ReadHoldingRegistersRequest(address=0, count=2))


@pytest.mark.asyncio
async def test_read_holding_registers_builds_request_and_returns_read_response() -> (
    None
):
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return ReadRegistersResponse(function_code=0x03, values=[10, 20])

    client.execute = fake_execute

    response = await client.read_holding_registers(address=0, count=2, unit_id=7)

    assert isinstance(captured["request"], ReadHoldingRegistersRequest)
    assert captured["request"].address == 0
    assert captured["request"].count == 2
    assert captured["unit_id"] == 7
    assert response.values == [10, 20]


@pytest.mark.asyncio
async def test_read_input_registers_builds_request_and_returns_read_response() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return ReadRegistersResponse(function_code=0x04, values=[10, 20])

    client.execute = fake_execute

    response = await client.read_input_registers(address=0, count=2, unit_id=7)

    assert isinstance(captured["request"], ReadInputRegistersRequest)
    assert captured["request"].address == 0
    assert captured["request"].count == 2
    assert captured["unit_id"] == 7
    assert response.values == [10, 20]


@pytest.mark.asyncio
async def test_write_single_register_verifies_echoed_address_and_value() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        return WriteSingleRegisterResponse(function_code=0x06, address=0, value=10)

    client.execute = fake_execute

    response = await client.write_single_register(address=0, value=10)

    assert isinstance(captured["request"], WriteSingleRegisterRequest)
    assert captured["request"].address == 0
    assert captured["request"].value == 10
    assert response.value == 10


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_address", "response_value"),
    [
        (1, 10),
        (0, 11),
    ],
)
async def test_write_single_register_rejects_mismatched_echo(
    response_address: int,
    response_value: int,
) -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

    async def fake_execute(request, unit_id=None):
        return WriteSingleRegisterResponse(
            function_code=0x06,
            address=response_address,
            value=response_value,
        )

    client.execute = fake_execute

    with pytest.raises(ValueError):
        await client.write_single_register(address=0, value=10)


@pytest.mark.asyncio
async def test_write_multiple_registers_verifies_echoed_address_and_count() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return WriteMultipleRegistersResponse(function_code=0x10, address=0, count=2)

    client.execute = fake_execute

    response = await client.write_multiple_registers(
        address=0,
        values=[10, 20],
        unit_id=7,
    )

    assert isinstance(captured["request"], WriteMultipleRegistersRequest)
    assert captured["request"].address == 0
    assert captured["request"].values == [10, 20]
    assert captured["unit_id"] == 7
    assert response.count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_address", "response_count"),
    [
        (1, 2),
        (0, 1),
    ],
)
async def test_write_multiple_registers_rejects_mismatched_echo(
    response_address: int,
    response_count: int,
) -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

    async def fake_execute(request, unit_id=None):
        return WriteMultipleRegistersResponse(
            function_code=0x10,
            address=response_address,
            count=response_count,
        )

    client.execute = fake_execute

    with pytest.raises(ValueError):
        await client.write_multiple_registers(address=0, values=[10, 20])
