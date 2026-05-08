from modbus import WriteMultipleRegistersResponse, ExceptionResponse, decode_response_pdu
import pytest

from modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleRegistersRequest,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)


def test_read_holding_registers_request_encodes_expected_pdu() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)
    assert request.encode() == bytes.fromhex("03 00 00 00 02")


def test_read_input_registers_request_encodes_expected_pdu() -> None:
    request = ReadInputRegistersRequest(address=0, count=2)
    assert request.encode() == bytes.fromhex("04 00 00 00 02")


def test_read_registers_response_decodes_register_values() -> None:
    response = ReadRegistersResponse.decode(
        function_code=0x03, payload=bytes.fromhex("04 00 0A 00 14")
    )

    assert response.function_code == 0x03
    assert response.values == [10, 20]


def test_read_registers_response_rejects_empty_payload() -> None:
    with pytest.raises(ValueError):
        ReadRegistersResponse.decode(function_code=0x03, payload=bytes.fromhex(""))


def test_read_registers_response_rejects_bad_byte_count() -> None:
    with pytest.raises(ValueError):
        ReadRegistersResponse.decode(
            function_code=0x03, payload=bytes.fromhex("04 00 0A")
        )
    with pytest.raises(ValueError):
        ReadRegistersResponse.decode(
            function_code=0x03, payload=bytes.fromhex("03 00 0A 00")
        )


def test_write_single_register_request_encodes_expected_pdu() -> None:
    request = WriteSingleRegisterRequest(address=0, value=1)
    assert request.encode() == bytes.fromhex("06 00 00 00 01")


def test_write_single_register_response_decodes_echo_payload() -> None:
    response = WriteSingleRegisterResponse.decode(bytes.fromhex("00 00 00 01"))
    assert response.function_code == 0x06
    assert response.address == 0
    assert response.value == 1


def test_write_multiple_registers_request_encodes_expected_pdu() -> None:
    request = WriteMultipleRegistersRequest(address=0, values=[10, 20])
    assert request.encode() == bytes.fromhex("10 00 00 00 02 04 00 0A 00 14")


def test_write_multiple_registers_response_decodes_echo_payload() -> None:
    response = WriteMultipleRegistersResponse.decode(bytes.fromhex("00 00 00 02"))
    assert response.address == 0
    assert response.count == 2


def test_exception_response_decodes_and_strips_exception_bit() -> None:
    response = ExceptionResponse.decode(function_code=0x83, payload=bytes.fromhex("02"))
    assert response.function_code == 0x03
    assert response.exception_code == 0x02


def test_decode_response_pdu_dispatches_by_request_type() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)
    data = bytes.fromhex("03 04 00 0A 00 14")
    response = decode_response_pdu(request=request, data=data)
    assert isinstance(response, ReadRegistersResponse)


def test_decode_response_pdu_rejects_mismatched_function_code() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)
    with pytest.raises(ValueError):
        decode_response_pdu(data=bytes.fromhex("04 04 00 0A 00 14"), request=request)
