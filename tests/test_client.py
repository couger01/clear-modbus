import pytest

from clear_modbus.client import ModbusTcpClient
from clear_modbus.constants import DEFAULT_MODBUS_TCP_PORT
from clear_modbus.exceptions import (
    ModbusExceptionResponseError,
    ModbusResponseMismatchError,
)
from clear_modbus.protocol.codec import ModbusTCPCodec
from clear_modbus.protocol.pdu import (
    DeviceIdentificationObject,
    ExceptionResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDeviceIdentificationRequest,
    ReadDeviceIdentificationResponse,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    ReadWriteMultipleRegistersRequest,
    WriteMultipleCoilsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleCoilRequest,
    WriteSingleCoilResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from clear_modbus.transport import TCPTransport


class FakeTransport:
    def __init__(self, receive_chunks: list[bytes] | None = None) -> None:
        self.receive_chunks = receive_chunks or []
        self.sent: list[bytes] = []
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False
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
    assert client.connected is False


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

    assert client.connected is False

    async with client as active_client:
        assert active_client is client
        assert client.connected is True
        assert transport.connected is True
        assert transport.closed is False

    assert client.connected is False
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
async def test_execute_decodes_interoperability_read_holding_registers_response() -> (
    None
):
    response_header = bytes.fromhex("00 01 00 00 00 09 11")
    response_pdu = bytes.fromhex("03 06 02 2B 00 00 00 64")
    transport = FakeTransport(receive_chunks=[response_header, response_pdu])
    client = ModbusTcpClient(host="127.0.0.1", unit_id=17)
    client.transport = transport

    response = await client.execute(
        ReadHoldingRegistersRequest(address=0x006B, count=3)
    )

    assert transport.sent == [bytes.fromhex("00 01 00 00 00 06 11 03 00 6B 00 03")]
    assert response == ReadRegistersResponse(function_code=0x03, values=[555, 0, 100])


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
async def test_execute_returns_raw_exception_response() -> None:
    response_header = bytes.fromhex("00 01 00 00 00 03 01")
    response_pdu = bytes.fromhex("83 02")

    transport = FakeTransport(receive_chunks=[response_header, response_pdu])
    client = ModbusTcpClient(host="127.0.0.1")
    client.transport = transport

    request = ReadHoldingRegistersRequest(address=0, count=2)

    response = await client.execute(request)

    assert response == ExceptionResponse(function_code=0x03, exception_code=0x02)


@pytest.mark.asyncio
async def test_read_coils_builds_request_and_returns_bit_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return ReadBitsResponse(function_code=0x01, values=[True, False])

    client.execute = fake_execute

    response = await client.read_coils(address=0, count=2, unit_id=7)

    assert isinstance(captured["request"], ReadCoilsRequest)
    assert captured["request"].address == 0
    assert captured["request"].count == 2
    assert captured["unit_id"] == 7
    assert response.values == [True, False]


@pytest.mark.asyncio
async def test_read_discrete_inputs_builds_request_and_returns_bit_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return ReadBitsResponse(function_code=0x02, values=[False, True])

    client.execute = fake_execute

    response = await client.read_discrete_inputs(address=0, count=2, unit_id=7)

    assert isinstance(captured["request"], ReadDiscreteInputsRequest)
    assert captured["request"].address == 0
    assert captured["request"].count == 2
    assert captured["unit_id"] == 7
    assert response.values == [False, True]


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
async def test_read_holding_registers_raises_for_exception_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return ExceptionResponse(function_code=0x03, exception_code=0x02)

    client.execute = fake_execute

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        await client.read_holding_registers(address=0, count=2)

    assert exc_info.value.function_code == 0x03
    assert exc_info.value.exception_code == 0x02


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
async def test_write_single_coil_verifies_echoed_address_and_value() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return WriteSingleCoilResponse(function_code=0x05, address=0, value=True)

    client.execute = fake_execute

    response = await client.write_single_coil(address=0, value=True, unit_id=7)

    assert isinstance(captured["request"], WriteSingleCoilRequest)
    assert captured["request"].address == 0
    assert captured["request"].value is True
    assert captured["unit_id"] == 7
    assert response.value is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_address", "response_value"),
    [
        (1, True),
        (0, False),
    ],
)
async def test_write_single_coil_rejects_mismatched_echo(
    response_address: int,
    response_value: bool,
) -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return WriteSingleCoilResponse(
            function_code=0x05,
            address=response_address,
            value=response_value,
        )

    client.execute = fake_execute

    with pytest.raises(ModbusResponseMismatchError):
        await client.write_single_coil(address=0, value=True)


@pytest.mark.asyncio
async def test_write_single_register_raises_for_exception_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return ExceptionResponse(function_code=0x06, exception_code=0x03)

    client.execute = fake_execute

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        await client.write_single_register(address=0, value=10)

    assert exc_info.value.function_code == 0x06
    assert exc_info.value.exception_code == 0x03


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

    with pytest.raises(ModbusResponseMismatchError):
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
async def test_read_write_multiple_registers_builds_request_and_returns_read_response() -> (
    None
):
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return ReadRegistersResponse(function_code=0x17, values=[55, 66])

    client.execute = fake_execute

    response = await client.read_write_multiple_registers(
        read_address=0,
        read_count=2,
        write_address=2,
        values=[10, 20],
        unit_id=7,
    )

    assert isinstance(captured["request"], ReadWriteMultipleRegistersRequest)
    assert captured["request"].read_address == 0
    assert captured["request"].read_count == 2
    assert captured["request"].write_address == 2
    assert captured["request"].values == [10, 20]
    assert captured["unit_id"] == 7
    assert response == ReadRegistersResponse(function_code=0x17, values=[55, 66])


@pytest.mark.asyncio
async def test_read_device_identification_builds_request_and_returns_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return ReadDeviceIdentificationResponse(
            read_code=1,
            conformity_level=1,
            objects=[DeviceIdentificationObject(object_id=0, value=b"Vendor")],
        )

    client.execute = fake_execute

    response = await client.read_device_identification(
        read_code=1,
        object_id=0,
        unit_id=7,
    )

    assert isinstance(captured["request"], ReadDeviceIdentificationRequest)
    assert captured["request"].read_code == 1
    assert captured["request"].object_id == 0
    assert captured["unit_id"] == 7
    assert response.objects == [
        DeviceIdentificationObject(object_id=0, value=b"Vendor")
    ]


@pytest.mark.asyncio
async def test_write_multiple_coils_verifies_echoed_address_and_count() -> None:
    client = ModbusTcpClient(host="127.0.0.1")
    captured: dict[str, object] = {}

    async def fake_execute(request, unit_id=None):
        captured["request"] = request
        captured["unit_id"] = unit_id
        return WriteMultipleCoilsResponse(function_code=0x0F, address=0, count=2)

    client.execute = fake_execute

    response = await client.write_multiple_coils(
        address=0,
        values=[True, False],
        unit_id=7,
    )

    assert isinstance(captured["request"], WriteMultipleCoilsRequest)
    assert captured["request"].address == 0
    assert captured["request"].values == [True, False]
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
async def test_write_multiple_coils_rejects_mismatched_echo(
    response_address: int,
    response_count: int,
) -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return WriteMultipleCoilsResponse(
            function_code=0x0F,
            address=response_address,
            count=response_count,
        )

    client.execute = fake_execute

    with pytest.raises(ModbusResponseMismatchError):
        await client.write_multiple_coils(address=0, values=[True, False])


@pytest.mark.asyncio
async def test_write_multiple_registers_raises_for_exception_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return ExceptionResponse(function_code=0x10, exception_code=0x03)

    client.execute = fake_execute

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        await client.write_multiple_registers(address=0, values=[10, 20])

    assert exc_info.value.function_code == 0x10
    assert exc_info.value.exception_code == 0x03


@pytest.mark.asyncio
async def test_read_write_multiple_registers_raises_for_exception_response() -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return ExceptionResponse(function_code=0x17, exception_code=0x03)

    client.execute = fake_execute

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        await client.read_write_multiple_registers(
            read_address=0,
            read_count=2,
            write_address=2,
            values=[10, 20],
        )

    assert exc_info.value.function_code == 0x17
    assert exc_info.value.exception_code == 0x03


@pytest.mark.asyncio
async def test_read_write_multiple_registers_rejects_wrong_response_type() -> None:
    client = ModbusTcpClient(host="127.0.0.1")

    async def fake_execute(request, unit_id=None):
        return WriteMultipleRegistersResponse(function_code=0x10, address=0, count=2)

    client.execute = fake_execute

    with pytest.raises(ModbusResponseMismatchError):
        await client.read_write_multiple_registers(
            read_address=0,
            read_count=2,
            write_address=2,
            values=[10, 20],
        )


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

    with pytest.raises(ModbusResponseMismatchError):
        await client.write_multiple_registers(address=0, values=[10, 20])
