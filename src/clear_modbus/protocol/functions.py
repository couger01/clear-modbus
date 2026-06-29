"""Modbus function and exception code helpers."""

from enum import IntEnum

__all__ = [
    "ExceptionCode",
    "FunctionCode",
    "add_exception_bit",
    "is_exception_function_code",
    "strip_exception_bit",
]


class FunctionCode(IntEnum):
    """Standard Modbus function codes supported by this package."""

    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10
    MASK_WRITE_REGISTER = 0x16
    READ_WRITE_MULTIPLE_REGISTERS = 0x17
    ENCAPSULATED_INTERFACE_TRANSPORT = 0x2B


class ExceptionCode(IntEnum):
    """Standard Modbus exception response codes."""

    ILLEGAL_FUNCTION = 0x01
    ILLEGAL_DATA_ADDRESS = 0x02
    ILLEGAL_DATA_VALUE = 0x03
    SERVER_DEVICE_FAILURE = 0x04
    ACKNOWLEDGE = 0x05
    SERVER_DEVICE_BUSY = 0x06
    MEMORY_PARITY_ERROR = 0x08
    GATEWAY_PATH_UNAVAILABLE = 0x0A
    GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND = 0x0B


def is_exception_function_code(function_code: int) -> bool:
    """Return whether the high exception bit is set.

    Parameters
    ----------
    function_code : int
        Function code byte.

    Returns
    -------
    bool
        ``True`` when bit ``0x80`` is set.

    """
    return bool(function_code & 0x80)


def strip_exception_bit(function_code: int) -> int:
    """Strip the high exception bit from a function code.

    Parameters
    ----------
    function_code : int
        Function code byte.

    Returns
    -------
    int
        Function code with bit ``0x80`` cleared.

    """
    return function_code & 0x7F


def add_exception_bit(function_code: int) -> int:
    """Set the high exception bit on a function code.

    Parameters
    ----------
    function_code : int
        Function code byte.

    Returns
    -------
    int
        Function code with bit ``0x80`` set.

    """
    return function_code | 0x80
