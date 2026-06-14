"""Public API for clear-modbus.

The distribution package is named ``clear-modbus`` and exposes the import
package ``clear_modbus``.
"""

from clear_modbus.client import ModbusTcpClient
from clear_modbus.exceptions import ModbusExceptionResponseError
from clear_modbus.protocol.pdu import (
    ExceptionResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    ReadWriteMultipleRegistersRequest,
    WriteMultipleCoilsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleCoilRequest,
    WriteSingleCoilResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
    decode_request_pdu,
    decode_response_pdu,
)
from clear_modbus.protocol.registry import (
    CustomFunctionCodeRegistry,
    RequestDecoder,
    ResponseDecoder,
    default_function_code_registry,
)
from clear_modbus.rtu_client import ModbusRtuClient
from clear_modbus.simulator import (
    BitRange,
    ModbusSimulator,
    RegisterRange,
    SimulatorProfile,
)

__all__ = [
    "BitRange",
    "CustomFunctionCodeRegistry",
    "ExceptionResponse",
    "ModbusExceptionResponseError",
    "ModbusRtuClient",
    "ModbusSimulator",
    "ModbusTcpClient",
    "ReadBitsResponse",
    "ReadCoilsRequest",
    "RequestDecoder",
    "ResponseDecoder",
    "ReadDiscreteInputsRequest",
    "ReadHoldingRegistersRequest",
    "ReadInputRegistersRequest",
    "ReadRegistersResponse",
    "ReadWriteMultipleRegistersRequest",
    "RegisterRange",
    "SimulatorProfile",
    "WriteMultipleCoilsRequest",
    "WriteMultipleCoilsResponse",
    "WriteMultipleRegistersRequest",
    "WriteMultipleRegistersResponse",
    "WriteSingleCoilRequest",
    "WriteSingleCoilResponse",
    "WriteSingleRegisterRequest",
    "WriteSingleRegisterResponse",
    "decode_request_pdu",
    "decode_response_pdu",
    "default_function_code_registry",
]
