import pytest

from clear_modbus.client_helpers import raise_for_exception_response
from clear_modbus.exceptions import (
    ModbusCRCError,
    ModbusExceptionResponse,
    ModbusExceptionResponseError,
    ModbusFrameError,
    ModbusProtocolError,
    ModbusResponseMismatchError,
)
from clear_modbus.protocol.pdu import ExceptionResponse, ReadRegistersResponse


def test_modbus_exception_response_stores_codes_and_message() -> None:
    error = ModbusExceptionResponse(function_code=0x03, exception_code=0x02)

    assert error.function_code == 0x03
    assert error.exception_code == 0x02
    assert "0x03" in str(error)
    assert "0x02" in str(error)


def test_protocol_specific_errors_inherit_from_protocol_error() -> None:
    assert issubclass(ModbusFrameError, ModbusProtocolError)
    assert issubclass(ModbusCRCError, ModbusFrameError)
    assert issubclass(ModbusResponseMismatchError, ModbusProtocolError)


def test_modbus_exception_response_error_is_public_exception_type() -> None:
    error = ModbusExceptionResponseError(function_code=0x03, exception_code=0x02)

    assert isinstance(error, ModbusExceptionResponse)
    assert error.function_code == 0x03
    assert error.exception_code == 0x02


def test_raise_for_exception_response_raises_for_exception_pdu() -> None:
    response = ExceptionResponse(function_code=0x03, exception_code=0x02)

    with pytest.raises(ModbusExceptionResponseError) as exc_info:
        raise_for_exception_response(response)

    assert exc_info.value.function_code == 0x03
    assert exc_info.value.exception_code == 0x02


def test_raise_for_exception_response_ignores_normal_response_pdu() -> None:
    response = ReadRegistersResponse(function_code=0x03, values=[10, 20])

    raise_for_exception_response(response)
