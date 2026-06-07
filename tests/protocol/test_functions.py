from clear_modbus.protocol.functions import (
    add_exception_bit,
    is_exception_function_code,
    strip_exception_bit,
)


def test_is_exception_function_code_detects_high_bit() -> None:
    assert is_exception_function_code(0x83) is True
    assert is_exception_function_code(0x03) is False


def test_strip_exception_bit_clears_high_bit() -> None:
    assert strip_exception_bit(0x83) == 0x03
    assert strip_exception_bit(0x03) == 0x03


def test_add_exception_bit_sets_high_bit() -> None:
    assert add_exception_bit(0x03) == 0x83
    assert add_exception_bit(0x83) == 0x83
