import pytest

from modbus import ReadRegistersResponse
from modbus.protocol.codec import ModbusTCPCodec, decode_tcp_frame, encode_tcp_frame
from modbus.protocol.mbap import ModbusTCPFrame
from modbus.protocol.pdu import ReadHoldingRegistersRequest


def test_encode_request_wraps_request_pdu_in_tcp_frame() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    payload = codec.encode_request(request=request, transaction_id=1, unit_id=1)

    assert payload == bytes.fromhex("00 01 00 00 00 06 01 03 00 00 00 02")


def test_decode_response_validates_transaction_id() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    data = bytes.fromhex("00 02 00 00 00 06 01 03 04 00 0A 00 14")
    with pytest.raises(ValueError):
        codec.decode_response(
            data=data, request=request, expected_transaction_id=1, expected_unit_id=1
        )


def test_decode_response_validates_unit_id() -> None:
    codec = ModbusTCPCodec()
    request = ReadHoldingRegistersRequest(address=0, count=2)

    data = bytes.fromhex("00 01 00 00 00 06 02 03 04 00 0A 00 14")
    with pytest.raises(ValueError):
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
