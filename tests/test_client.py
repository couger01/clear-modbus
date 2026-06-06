import pytest

from modbus.client import ModbusTcpClient
from modbus.constants import DEFAULT_MODBUS_TCP_PORT
from modbus.protocol.codec import ModbusTCPCodec
from modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from modbus.transport import TCPTransport


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


def test_client_initializes_transport_codec_and_transaction_counter() -> None:
    client = ModbusTcpClient(
        host="127.0.0.1", port=DEFAULT_MODBUS_TCP_PORT, unit_id=1, timeout=5
    )
    assert client.host == "127.0.0.1"
    assert client.port == DEFAULT_MODBUS_TCP_PORT
    assert client.unit_id == 1
    assert client.timeout == 5
    assert isinstance(client.codec, ModbusTCPCodec)
    assert isinstance(client.transport, TCPTransport)


def test_next_transaction_id_starts_at_one_and_wraps() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    assert client._next_transaction_id() == 1

    client._transaction_id = 0xFFFF
    assert client._next_transaction_id() == 0xFFFF
    assert client._next_transaction_id() == 1


@pytest.mark.asyncio
async def test_client_context_manager_connects_and_closes() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    transport = FakeTransport()
    client.transport = transport

    async with client as active_client:
        assert active_client is client
        assert transport.connected is True
        assert transport.closed is False

    assert transport.closed is True


@pytest.mark.asyncio
async def test_execute_sends_encoded_request_and_decodes_response() -> None:
    response_header = bytes.fromhex("00 01 00 00 00 07 01")
    response_pdu = bytes.fromhex("03 04 00 0A 00 14")

    transport = FakeTransport(receive_chunks=[response_header, response_pdu])
    client = ModbusTcpClient(host="127.0.0.1")
    client.transport = transport

    request = ReadHoldingRegistersRequest(address=0, count=2)

    response = await client.execute(request)

    assert client.transport.sent == [
        bytes.fromhex("00 01 00 00 00 06 01 03 00 00 00 02")
    ]

    assert isinstance(response, ReadRegistersResponse)
    assert response.values == [10, 20]


@pytest.mark.asyncio
async def test_execute_uses_unit_id_override() -> None:
    response_header = bytes.fromhex("00 01 00 00 00 07 02")
    response_pdu = bytes.fromhex("03 04 00 0A 00 14")

    transport = FakeTransport(receive_chunks=[response_header, response_pdu])
    client = ModbusTcpClient(host="127.0.0.1")
    client.transport = transport

    request = ReadHoldingRegistersRequest(address=0, count=2)

    response = await client.execute(request, unit_id=2)

    assert client.transport.sent == [
        bytes.fromhex("00 01 00 00 00 06 02 03 00 00 00 02")
    ]

    assert isinstance(response, ReadRegistersResponse)


@pytest.mark.asyncio
async def test_read_holding_registers_builds_request_and_returns_read_response() -> (
    None
):
    client = ModbusTcpClient(host="127.0.0.1")
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

    assert response.function_code == 0x03
    assert response.values == [10, 20]


@pytest.mark.asyncio
async def test_read_input_registers_builds_request_and_returns_read_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
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

    assert response.function_code == 0x04
    assert response.values == [10, 20]


@pytest.mark.asyncio
async def test_write_single_register_verifies_echoed_address_and_value() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return WriteSingleRegisterResponse(function_code=0x06, address=0, value=10)

    client.execute = fake_execute

    response = await client.write_single_register(address=0, value=10)

    assert isinstance(captured["request"], WriteSingleRegisterRequest)
    assert captured["request"].address == 0
    assert captured["request"].value == 10

    assert response.function_code == 0x06
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
    client = ModbusTcpClient(host="127.0.0.1")

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
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return WriteMultipleRegistersResponse(function_code=0x10, address=0, count=2)

    client.execute = fake_execute

    response = await client.write_multiple_registers(
        address=0, values=[10, 20], unit_id=7
    )

    assert isinstance(captured["request"], WriteMultipleRegistersRequest)
    assert captured["request"].address == 0
    assert captured["request"].values == [10, 20]
    assert captured["unit_id"] == 7

    assert response.function_code == 0x10
    assert response.address == 0
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
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return WriteMultipleRegistersResponse(
            function_code=0x10,
            address=response_address,
            count=response_count,
        )

    client.execute = fake_execute

    with pytest.raises(ValueError):
        await client.write_multiple_registers(address=0, values=[10, 20])
