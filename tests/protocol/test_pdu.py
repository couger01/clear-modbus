import pytest

from clear_modbus import (
    ExceptionResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDiscreteInputsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersResponse,
    WriteSingleCoilResponse,
    decode_request_pdu,
    decode_response_pdu,
)
from clear_modbus.exceptions import ModbusPDUError
from clear_modbus.protocol.functions import FunctionCode
from clear_modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleCoilsRequest,
    WriteMultipleRegistersRequest,
    WriteSingleCoilRequest,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
    pack_bits,
    unpack_bits,
)

INTEROPERABILITY_PDU_CASES = [
    pytest.param(
        FunctionCode.READ_COILS,
        ReadCoilsRequest(address=0, count=9),
        bytes.fromhex("01 00 00 00 09"),
        bytes.fromhex("01 02 8D 01"),
        ReadBitsResponse(
            function_code=0x01,
            values=[True, False, True, True, False, False, False, True, True],
        ),
        id="read-coils",
    ),
    pytest.param(
        FunctionCode.READ_DISCRETE_INPUTS,
        ReadDiscreteInputsRequest(address=0, count=2),
        bytes.fromhex("02 00 00 00 02"),
        bytes.fromhex("02 01 02"),
        ReadBitsResponse(function_code=0x02, values=[False, True]),
        id="read-discrete-inputs",
    ),
    pytest.param(
        FunctionCode.READ_HOLDING_REGISTERS,
        ReadHoldingRegistersRequest(address=0x006B, count=3),
        bytes.fromhex("03 00 6B 00 03"),
        bytes.fromhex("03 06 02 2B 00 00 00 64"),
        ReadRegistersResponse(function_code=0x03, values=[555, 0, 100]),
        id="read-holding-registers",
    ),
    pytest.param(
        FunctionCode.READ_INPUT_REGISTERS,
        ReadInputRegistersRequest(address=0, count=2),
        bytes.fromhex("04 00 00 00 02"),
        bytes.fromhex("04 04 00 0A 00 14"),
        ReadRegistersResponse(function_code=0x04, values=[10, 20]),
        id="read-input-registers",
    ),
    pytest.param(
        FunctionCode.WRITE_SINGLE_COIL,
        WriteSingleCoilRequest(address=0, value=True),
        bytes.fromhex("05 00 00 FF 00"),
        bytes.fromhex("05 00 00 FF 00"),
        WriteSingleCoilResponse(function_code=0x05, address=0, value=True),
        id="write-single-coil",
    ),
    pytest.param(
        FunctionCode.WRITE_SINGLE_REGISTER,
        WriteSingleRegisterRequest(address=0, value=1),
        bytes.fromhex("06 00 00 00 01"),
        bytes.fromhex("06 00 00 00 01"),
        WriteSingleRegisterResponse(function_code=0x06, address=0, value=1),
        id="write-single-register",
    ),
    pytest.param(
        FunctionCode.WRITE_MULTIPLE_COILS,
        WriteMultipleCoilsRequest(
            address=0,
            values=[True, False, True, True, False, False, False, True, True],
        ),
        bytes.fromhex("0F 00 00 00 09 02 8D 01"),
        bytes.fromhex("0F 00 00 00 09"),
        WriteMultipleCoilsResponse(function_code=0x0F, address=0, count=9),
        id="write-multiple-coils",
    ),
    pytest.param(
        FunctionCode.WRITE_MULTIPLE_REGISTERS,
        WriteMultipleRegistersRequest(address=0, values=[10, 20]),
        bytes.fromhex("10 00 00 00 02 04 00 0A 00 14"),
        bytes.fromhex("10 00 00 00 02"),
        WriteMultipleRegistersResponse(function_code=0x10, address=0, count=2),
        id="write-multiple-registers",
    ),
]


@pytest.mark.parametrize(
    "function_code,request_pdu_obj,request_pdu,response_pdu,expected_response",
    INTEROPERABILITY_PDU_CASES,
)
def test_pdu_interoperability_function_code(
    function_code,
    request_pdu_obj,
    request_pdu,
    response_pdu,
    expected_response,
) -> None:
    assert request_pdu_obj.function_code == function_code
    assert request_pdu_obj.encode() == request_pdu
    assert decode_request_pdu(request_pdu) == request_pdu_obj
    assert (
        decode_response_pdu(request=request_pdu_obj, data=response_pdu)
        == expected_response
    )
    assert decode_response_pdu(
        request=request_pdu_obj,
        data=bytes([function_code | 0x80, 0x02]),
    ) == ExceptionResponse(function_code=function_code, exception_code=0x02)


def test_read_holding_registers_request_encodes_expected_pdu() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)
    assert request.encode() == bytes.fromhex("03 00 00 00 02")


def test_read_input_registers_request_encodes_expected_pdu() -> None:
    request = ReadInputRegistersRequest(address=0, count=2)
    assert request.encode() == bytes.fromhex("04 00 00 00 02")


def test_pack_bits_uses_lsb_first_bit_order() -> None:
    values = [True, False, True, True, False, False, False, True, True]

    assert pack_bits(values) == bytes.fromhex("8D 01")
    assert unpack_bits(bytes.fromhex("8D 01"), len(values)) == values


def test_read_coils_request_encodes_expected_pdu() -> None:
    request = ReadCoilsRequest(address=0, count=10)

    assert request.encode() == bytes.fromhex("01 00 00 00 0A")


def test_read_discrete_inputs_request_encodes_expected_pdu() -> None:
    request = ReadDiscreteInputsRequest(address=0, count=10)

    assert request.encode() == bytes.fromhex("02 00 00 00 0A")


def test_read_bits_response_decodes_bit_values() -> None:
    response = ReadBitsResponse.decode(
        function_code=0x01,
        payload=bytes.fromhex("02 8D 01"),
        count=9,
    )

    assert response.function_code == 0x01
    assert response.values == [
        True,
        False,
        True,
        True,
        False,
        False,
        False,
        True,
        True,
    ]


def test_read_bits_response_rejects_bad_byte_count() -> None:
    with pytest.raises(ValueError):
        ReadBitsResponse.decode(
            function_code=0x01, payload=bytes.fromhex("02 8D"), count=9
        )


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


def test_write_single_coil_request_encodes_expected_pdu() -> None:
    request = WriteSingleCoilRequest(address=0, value=True)

    assert request.encode() == bytes.fromhex("05 00 00 FF 00")


def test_write_single_coil_response_decodes_echo_payload() -> None:
    response = WriteSingleCoilResponse.decode(bytes.fromhex("00 00 FF 00"))

    assert response.function_code == 0x05
    assert response.address == 0
    assert response.value is True


def test_write_single_register_response_decodes_echo_payload() -> None:
    response = WriteSingleRegisterResponse.decode(bytes.fromhex("00 00 00 01"))
    assert response.function_code == 0x06
    assert response.address == 0
    assert response.value == 1


def test_write_multiple_registers_request_encodes_expected_pdu() -> None:
    request = WriteMultipleRegistersRequest(address=0, values=[10, 20])
    assert request.encode() == bytes.fromhex("10 00 00 00 02 04 00 0A 00 14")


def test_write_multiple_coils_request_encodes_expected_pdu() -> None:
    request = WriteMultipleCoilsRequest(
        address=0,
        values=[True, False, True, True, False, False, False, True, True],
    )

    assert request.encode() == bytes.fromhex("0F 00 00 00 09 02 8D 01")


def test_write_multiple_coils_response_decodes_echo_payload() -> None:
    response = WriteMultipleCoilsResponse.decode(bytes.fromhex("00 00 00 09"))

    assert response.function_code == 0x0F
    assert response.address == 0
    assert response.count == 9


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


def test_decode_response_pdu_dispatches_bit_response_by_request_type() -> None:
    request = ReadCoilsRequest(address=0, count=9)
    data = bytes.fromhex("01 02 8D 01")

    response = decode_response_pdu(request=request, data=data)

    assert response == ReadBitsResponse(
        function_code=0x01,
        values=[True, False, True, True, False, False, False, True, True],
    )


def test_decode_response_pdu_rejects_mismatched_function_code() -> None:
    request = ReadHoldingRegistersRequest(address=0, count=2)
    with pytest.raises(ValueError):
        decode_response_pdu(data=bytes.fromhex("04 04 00 0A 00 14"), request=request)


def test_decode_request_pdu_decodes_read_holding_registers_request() -> None:
    request = decode_request_pdu(bytes.fromhex("03 00 00 00 02"))

    assert request == ReadHoldingRegistersRequest(address=0, count=2)


def test_decode_request_pdu_decodes_read_coils_request() -> None:
    request = decode_request_pdu(bytes.fromhex("01 00 00 00 0A"))

    assert request == ReadCoilsRequest(address=0, count=10)


def test_decode_request_pdu_decodes_read_discrete_inputs_request() -> None:
    request = decode_request_pdu(bytes.fromhex("02 00 00 00 0A"))

    assert request == ReadDiscreteInputsRequest(address=0, count=10)


def test_decode_request_pdu_decodes_read_input_registers_request() -> None:
    request = decode_request_pdu(bytes.fromhex("04 00 00 00 02"))

    assert request == ReadInputRegistersRequest(address=0, count=2)


def test_decode_request_pdu_decodes_write_single_register_request() -> None:
    request = decode_request_pdu(bytes.fromhex("06 00 00 00 01"))

    assert request == WriteSingleRegisterRequest(address=0, value=1)


def test_decode_request_pdu_decodes_write_single_coil_request() -> None:
    request = decode_request_pdu(bytes.fromhex("05 00 00 FF 00"))

    assert request == WriteSingleCoilRequest(address=0, value=True)


def test_decode_request_pdu_decodes_write_multiple_registers_request() -> None:
    request = decode_request_pdu(bytes.fromhex("10 00 00 00 02 04 00 0A 00 14"))

    assert request == WriteMultipleRegistersRequest(address=0, values=[10, 20])


def test_decode_request_pdu_decodes_write_multiple_coils_request() -> None:
    request = decode_request_pdu(bytes.fromhex("0F 00 00 00 09 02 8D 01"))

    assert request == WriteMultipleCoilsRequest(
        address=0,
        values=[True, False, True, True, False, False, False, True, True],
    )


def test_decode_request_pdu_rejects_empty_data() -> None:
    with pytest.raises(ValueError):
        decode_request_pdu(b"")


def test_decode_request_pdu_rejects_bad_payload_length() -> None:
    with pytest.raises(ValueError):
        decode_request_pdu(bytes.fromhex("03 00 00 00"))


def test_decode_request_pdu_rejects_bad_write_multiple_byte_count() -> None:
    with pytest.raises(ValueError):
        decode_request_pdu(bytes.fromhex("10 00 00 00 02 06 00 0A 00 14"))


def test_decode_request_pdu_rejects_unsupported_function_code() -> None:
    with pytest.raises(ModbusPDUError):
        decode_request_pdu(bytes.fromhex("11 00 00 00 01"))
