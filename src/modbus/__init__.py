"""Public API for clear-modbus.

The distribution package is named ``clear-modbus`` and exposes the import
package ``modbus``.
"""

from modbus.client import ModbusTcpClient
from modbus.exceptions import ModbusExceptionResponseError
from modbus.protocol.pdu import (
    ExceptionResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
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
from modbus.rtu_client import ModbusRtuClient
from modbus.simulator import BitRange, ModbusSimulator, RegisterRange, SimulatorProfile

__all__ = [
    "BitRange",
    "ExceptionResponse",
    "ModbusExceptionResponseError",
    "ModbusRtuClient",
    "ModbusSimulator",
    "ModbusTcpClient",
    "ReadBitsResponse",
    "ReadCoilsRequest",
    "ReadDiscreteInputsRequest",
    "ReadHoldingRegistersRequest",
    "ReadInputRegistersRequest",
    "ReadRegistersResponse",
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
]
