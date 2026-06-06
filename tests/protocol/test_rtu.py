import pytest

from modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleRegistersRequest,
    WriteSingleRegisterRequest,
)
from modbus.protocol.rtu import (
    RTU_EXCEPTION_RESPONSE_SIZE,
    RTU_RESPONSE_PREFIX_SIZE,
    RTU_WRITE_REGISTER_RESPONSE_SIZE,
    ModbusRTUCodec,
    ModbusRTUFrame,
    crc16_modbus,
    decode_rtu_frame,
    encode_rtu_frame,
    fixed_rtu_response_size,
    rtu_read_register_response_size,
    rtu_response_size_from_prefix,
)


def test_crc16_modbus_matches_known_request_vector() -> None:
    data = bytes.fromhex("01 03 00 00 00 0A")

    crc = crc16_modbus(data)

    assert crc == 0xCDC5
    assert crc.to_bytes(2, "little") == bytes.fromhex("C5 CD")


def test_rtu_frame_encodes_unit_id_pdu_and_crc() -> None:
    frame = ModbusRTUFrame(
        unit_id=1,
        pdu=bytes.fromhex("03 00 00 00 0A"),
    )

    assert frame.encode() == bytes.fromhex("01 03 00 00 00 0A C5 CD")


def test_rtu_frame_decodes_unit_id_and_pdu() -> None:
    frame = ModbusRTUFrame.decode(bytes.fromhex("01 03 00 00 00 0A C5 CD"))

    assert frame.unit_id == 1
    assert frame.pdu == bytes.fromhex("03 00 00 00 0A")


def test_rtu_frame_rejects_short_frame() -> None:
    with pytest.raises(ValueError):
        ModbusRTUFrame.decode(bytes.fromhex("01 03 C5"))


def test_rtu_frame_rejects_bad_crc() -> None:
    with pytest.raises(ValueError):
        ModbusRTUFrame.decode(bytes.fromhex("01 03 00 00 00 0A 00 00"))


def test_encode_rtu_frame_delegates_to_frame_encode() -> None:
    frame = ModbusRTUFrame(
        unit_id=1,
        pdu=bytes.fromhex("03 00 00 00 0A"),
    )

    assert encode_rtu_frame(frame) == frame.encode()


def test_decode_rtu_frame_delegates_to_frame_decode() -> None:
    data = bytes.fromhex("01 03 00 00 00 0A C5 CD")

    assert decode_rtu_frame(data) == ModbusRTUFrame.decode(data)


def test_rtu_codec_encodes_request_pdu_in_rtu_frame() -> None:
    codec = ModbusRTUCodec()
    request = ReadHoldingRegistersRequest(address=0, count=10)

    payload = codec.encode_request(request=request, unit_id=1)

    assert payload == bytes.fromhex("01 03 00 00 00 0A C5 CD")


def test_rtu_codec_validates_response_unit_id() -> None:
    codec = ModbusRTUCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)
    response = ModbusRTUFrame(
        unit_id=2,
        pdu=bytes.fromhex("03 04 00 0A 00 14"),
    ).encode()

    with pytest.raises(ValueError):
        codec.decode_response(
            data=response,
            request=request,
            expected_unit_id=1,
        )


def test_rtu_codec_decodes_response_pdu() -> None:
    codec = ModbusRTUCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)
    response = ModbusRTUFrame(
        unit_id=1,
        pdu=bytes.fromhex("03 04 00 0A 00 14"),
    ).encode()

    decoded_response = codec.decode_response(
        data=response,
        request=request,
        expected_unit_id=1,
    )

    assert decoded_response == ReadRegistersResponse(
        function_code=0x03,
        values=[10, 20],
    )


def test_rtu_exception_response_size_is_fixed() -> None:
    assert RTU_EXCEPTION_RESPONSE_SIZE == 5


def test_rtu_response_prefix_size_is_unit_id_plus_function_code() -> None:
    assert RTU_RESPONSE_PREFIX_SIZE == 2


@pytest.mark.parametrize(
    "request_pdu",
    [
        WriteSingleRegisterRequest(address=0, value=1),
        WriteMultipleRegistersRequest(address=0, values=[10, 20]),
    ],
)
def test_fixed_rtu_response_size_returns_write_echo_size(request_pdu) -> None:
    assert fixed_rtu_response_size(request_pdu) == RTU_WRITE_REGISTER_RESPONSE_SIZE


@pytest.mark.parametrize(
    "request_pdu",
    [
        ReadHoldingRegistersRequest(address=0, count=2),
        ReadInputRegistersRequest(address=0, count=2),
    ],
)
def test_fixed_rtu_response_size_returns_none_for_variable_read_size(
    request_pdu,
) -> None:
    assert fixed_rtu_response_size(request_pdu) is None


def test_rtu_response_size_from_prefix_returns_exception_size() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)

    assert (
        rtu_response_size_from_prefix(bytes.fromhex("01 83"), request)
        == RTU_EXCEPTION_RESPONSE_SIZE
    )


def test_rtu_response_size_from_prefix_returns_fixed_write_size() -> None:
    request = WriteSingleRegisterRequest(address=0, value=1)

    assert (
        rtu_response_size_from_prefix(bytes.fromhex("01 06"), request)
        == RTU_WRITE_REGISTER_RESPONSE_SIZE
    )


def test_rtu_response_size_from_prefix_returns_none_for_read_registers() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)

    assert rtu_response_size_from_prefix(bytes.fromhex("01 03"), request) is None


def test_rtu_response_size_from_prefix_rejects_bad_prefix_length() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)

    with pytest.raises(ValueError):
        rtu_response_size_from_prefix(bytes.fromhex("01"), request)


def test_rtu_read_register_response_size_uses_byte_count() -> None:
    assert rtu_read_register_response_size(4) == 9


def test_rtu_read_register_response_size_rejects_odd_byte_count() -> None:
    with pytest.raises(ValueError):
        rtu_read_register_response_size(3)
