import pytest

from clear_modbus.exceptions import (
    ModbusCRCError,
    ModbusExceptionResponseError,
    ModbusResponseMismatchError,
)
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
    WriteMultipleCoilsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleCoilRequest,
    WriteSingleCoilResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from clear_modbus.protocol.rtu import ModbusRTUFrame
from clear_modbus.rtu_client import ModbusRtuClient
from clear_modbus.transport import SerialTransport


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


def split_rtu_response(frame: ModbusRTUFrame) -> list[bytes]:
    data = frame.encode()
    function_code = data[1]
    if function_code & 0x80:
        return [data[:2], data[2:]]
    if function_code in (0x01, 0x02, 0x03, 0x04):
        return [data[:2], data[2:3], data[3:]]
    return [data[:2], data[2:]]


def test_rtu_client_initializes_serial_transport_and_codec() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", unit_id=1, baudrate=19200, timeout=2)

    assert client.port == "/dev/ttyUSB0"
    assert client.unit_id == 1
    assert client.baudrate == 19200
    assert client.timeout == 2
    assert isinstance(client.transport, SerialTransport)
    assert client.connected is False


@pytest.mark.asyncio
async def test_rtu_client_context_manager_connects_and_closes() -> None:
    transport = FakeTransport()
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    assert client.connected is False

    async with client as active_client:
        assert active_client is client
        assert client.connected is True
        assert transport.connected is True
        assert transport.closed is False

    assert client.connected is False
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
async def test_execute_decodes_interoperability_byte_count_read_response() -> None:
    response = bytes.fromhex("11 03 06 02 2B 00 00 00 64 C8 BA")
    transport = FakeTransport(
        receive_chunks=[response[:2], response[2:3], response[3:]]
    )
    client = ModbusRtuClient(port="/dev/ttyUSB0", unit_id=17, transport=transport)

    decoded_response = await client.execute(
        ReadHoldingRegistersRequest(address=0x006B, count=3)
    )

    assert transport.sent == [bytes.fromhex("11 03 00 6B 00 03 76 87")]
    assert decoded_response == ReadRegistersResponse(
        function_code=0x03,
        values=[555, 0, 100],
    )


@pytest.mark.asyncio
async def test_execute_decodes_read_device_identification_response() -> None:
    response_frame = ModbusRTUFrame(
        unit_id=1,
        pdu=ReadDeviceIdentificationResponse(
            read_code=1,
            conformity_level=1,
            objects=[DeviceIdentificationObject(object_id=0, value=b"Vendor")],
        ).encode(),
    ).encode()
    transport = FakeTransport(
        receive_chunks=[
            response_frame[:2],
            response_frame[2:8],
            response_frame[8:10],
            response_frame[10:16],
            response_frame[16:],
        ]
    )
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    decoded_response = await client.execute(
        ReadDeviceIdentificationRequest(read_code=1, object_id=0)
    )

    assert transport.sent == [bytes.fromhex("01 2B 0E 01 00 70 77")]
    assert decoded_response == ReadDeviceIdentificationResponse(
        read_code=1,
        conformity_level=1,
        objects=[DeviceIdentificationObject(object_id=0, value=b"Vendor")],
    )


@pytest.mark.asyncio
async def test_execute_decodes_interoperability_fixed_write_echo() -> None:
    response = bytes.fromhex("11 06 00 6B 00 03 BA 87")
    transport = FakeTransport(receive_chunks=[response[:2], response[2:]])
    client = ModbusRtuClient(port="/dev/ttyUSB0", unit_id=17, transport=transport)

    decoded_response = await client.execute(
        WriteSingleRegisterRequest(address=0x006B, value=3)
    )

    assert transport.sent == [bytes.fromhex("11 06 00 6B 00 03 BA 87")]
    assert decoded_response == WriteSingleRegisterResponse(
        function_code=0x06,
        address=0x006B,
        value=3,
    )


@pytest.mark.asyncio
async def test_execute_decodes_interoperability_exception_response() -> None:
    response = bytes.fromhex("11 83 02 C1 34")
    transport = FakeTransport(receive_chunks=[response[:2], response[2:]])
    client = ModbusRtuClient(port="/dev/ttyUSB0", unit_id=17, transport=transport)

    decoded_response = await client.execute(
        ReadHoldingRegistersRequest(address=0x006B, count=3)
    )

    assert transport.sent == [bytes.fromhex("11 03 00 6B 00 03 76 87")]
    assert decoded_response == ExceptionResponse(
        function_code=0x03, exception_code=0x02
    )


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
async def test_execute_decodes_read_coils_response() -> None:
    response_frame = ModbusRTUFrame(
        unit_id=1,
        pdu=ReadBitsResponse(function_code=0x01, values=[True, False]).encode(),
    )
    transport = FakeTransport(receive_chunks=split_rtu_response(response_frame))
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=transport)

    request = ReadCoilsRequest(address=0, count=2)
    response = await client.execute(request)

    assert response == ReadBitsResponse(function_code=0x01, values=[True, False])


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
async def test_execute_returns_raw_exception_response() -> None:
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

    with pytest.raises(ModbusCRCError):
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
async def test_read_coils_builds_request_and_returns_bit_response() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
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
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
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
async def test_read_holding_registers_raises_for_exception_response() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

    async def fake_execute(request, unit_id=None):
        return ExceptionResponse(function_code=0x03, exception_code=0x02)

    client.execute = fake_execute

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        await client.read_holding_registers(address=0, count=2)

    assert exc_info.value.function_code == 0x03
    assert exc_info.value.exception_code == 0x02


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
async def test_write_single_coil_verifies_echoed_address_and_value() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
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
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

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
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

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
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

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
async def test_write_multiple_coils_verifies_echoed_address_and_count() -> None:
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())
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
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

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
    client = ModbusRtuClient(port="/dev/ttyUSB0", transport=FakeTransport())

    async def fake_execute(request, unit_id=None):
        return ExceptionResponse(function_code=0x10, exception_code=0x03)

    client.execute = fake_execute

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        await client.write_multiple_registers(address=0, values=[10, 20])

    assert exc_info.value.function_code == 0x10
    assert exc_info.value.exception_code == 0x03


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

    with pytest.raises(ModbusResponseMismatchError):
        await client.write_multiple_registers(address=0, values=[10, 20])
