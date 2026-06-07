from dataclasses import dataclass
from typing import ClassVar

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
from clear_modbus.protocol.registry import default_function_code_registry


@dataclass(frozen=True)
class CustomCodecRequest:
    value: int

    function_code: ClassVar[int] = 0x41

    def encode(self) -> bytes:
        return bytes([self.function_code, self.value])


@dataclass(frozen=True)
class CustomCodecResponse:
    value: int
    request_value: int

    function_code: ClassVar[int] = 0x41

    def encode(self) -> bytes:
        return bytes([self.function_code, self.value])


@pytest.fixture
def function_code_registry():
    request_decoders = default_function_code_registry.request_decoders.copy()
    response_decoders = default_function_code_registry.response_decoders.copy()
    try:
        yield default_function_code_registry
    finally:
        default_function_code_registry.request_decoders.clear()
        default_function_code_registry.request_decoders.update(request_decoders)
        default_function_code_registry.response_decoders.clear()
        default_function_code_registry.response_decoders.update(response_decoders)


def test_tcp_codec_uses_custom_function_code_response_decoder(
    function_code_registry,
) -> None:
    codec = ModbusTCPCodec()
    request = CustomCodecRequest(value=10)

    def decode_custom_response(payload: bytes, request_pdu) -> CustomCodecResponse:
        assert isinstance(request_pdu, CustomCodecRequest)
        return CustomCodecResponse(value=payload[0], request_value=request_pdu.value)

    function_code_registry.register_response_decoder(0x41, decode_custom_response)

    response = codec.decode_response(
        data=bytes.fromhex("00 01 00 00 00 03 11 41 14"),
        request=request,
        expected_transaction_id=1,
        expected_unit_id=17,
    )

    assert response == CustomCodecResponse(value=20, request_value=10)


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
