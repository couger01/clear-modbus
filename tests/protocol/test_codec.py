import pytest

from clear_modbus import ReadRegistersResponse
from clear_modbus.exceptions import ModbusResponseMismatchError
from clear_modbus.protocol.codec import (
    ModbusTCPCodec,
    decode_tcp_frame,
    encode_tcp_frame,
)
from clear_modbus.protocol.mbap import ModbusTCPFrame
from clear_modbus.protocol.pdu import ReadHoldingRegistersRequest


def test_tcp_codec_decodes_interoperability_read_holding_registers_response() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0x006B, count=3)
    response_adu = bytes.fromhex("00 01 00 00 00 09 11 03 06 02 2B 00 00 00 64")

    response = codec.decode_response(
        data=response_adu,
        request=request,
        expected_transaction_id=1,
        expected_unit_id=17,
    )

    assert response == ReadRegistersResponse(function_code=0x03, values=[555, 0, 100])


def test_tcp_codec_encodes_interoperability_read_holding_registers_request() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0x006B, count=3)

    adu = codec.encode_request(request=request, transaction_id=1, unit_id=17)

    assert adu == bytes.fromhex("00 01 00 00 00 06 11 03 00 6B 00 03")


def test_encode_request_wraps_request_pdu_in_tcp_frame() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    payload = codec.encode_request(request=request, transaction_id=1, unit_id=1)

    assert payload == bytes.fromhex("00 01 00 00 00 06 01 03 00 00 00 02")


def test_decode_response_validates_transaction_id() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    data = bytes.fromhex("00 02 00 00 00 07 01 03 04 00 0A 00 14")
    with pytest.raises(ModbusResponseMismatchError):
        codec.decode_response(
            data=data, request=request, expected_transaction_id=1, expected_unit_id=1
        )


def test_decode_response_validates_unit_id() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    data = bytes.fromhex("00 01 00 00 00 07 02 03 04 00 0A 00 14")
    with pytest.raises(ModbusResponseMismatchError):
        codec.decode_response(
            data=data, request=request, expected_transaction_id=1, expected_unit_id=1
        )


def test_decode_response_returns_decoded_response_pdu() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    frame = ModbusTCPFrame(
        transaction_id=1, unit_id=1, pdu=bytes.fromhex("03 04 00 0A 00 14")
    )
    response = codec.decode_response(
        data=frame.encode(),
        request=request,
        expected_transaction_id=1,
        expected_unit_id=1,
    )
    assert isinstance(response, ReadRegistersResponse)


def test_encode_tcp_frame_delegates_to_frame_encode() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)

    payload = request.encode()
    frame = ModbusTCPFrame(transaction_id=1, unit_id=1, pdu=payload)
    assert encode_tcp_frame(frame) == frame.encode()


def test_decode_tcp_frame_delegates_to_frame_decode() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)

    payload = request.encode()
    frame = ModbusTCPFrame(transaction_id=1, unit_id=1, pdu=payload)
    data = frame.encode()
    assert decode_tcp_frame(data) == ModbusTCPFrame.decode(data)
