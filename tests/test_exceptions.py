from modbus.exceptions import ModbusExceptionResponse


def test_modbus_exception_response_stores_codes_and_message() -> None:
    error = ModbusExceptionResponse(function_code=0x03, exception_code=0x02)

    assert error.function_code == 0x03
    assert error.exception_code == 0x02
    assert "0x03" in str(error)
    assert "0x02" in str(error)
