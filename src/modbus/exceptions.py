class ModbusError(Exception):
    """Base exception for this Modbus package."""


class ModbusTransportError(ModbusError):
    """Raised when the transport layer fails."""


class ModbusTimeoutError(ModbusTransportError):
    """Raised when a Modbus operation exceeds its configured timeout."""


class ModbusConnectionError(ModbusTransportError):
    """Raised when a connection cannot be opened or is lost unexpectedly."""


class ModbusProtocolError(ModbusError):
    """Raised when bytes on the wire violate the Modbus protocol."""


class ModbusFrameError(ModbusProtocolError):
    """Raised when an ADU/MBAP frame is malformed."""


class ModbusPDUError(ModbusProtocolError):
    """Raised when a PDU is malformed or unsupported."""


class ModbusExceptionResponse(ModbusProtocolError):
    function_code: int
    exception_code: int

    def __init__(self, function_code: int, exception_code: int) -> None:
        self.function_code = function_code
        self.exception_code = exception_code
        super().__init__(
            f"Modbus exception response: function_code=0x{function_code:02X}, "
            f"exception_code=0x{exception_code:02X}"
        )
