"""Protocol microbenchmarks for clear-modbus."""

from __future__ import annotations

import pyperf

from clear_modbus.protocol.mbap import MBAPHeader, ModbusTCPFrame
from clear_modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadRegistersResponse,
    RequestPDU,
    WriteMultipleCoilsRequest,
    WriteMultipleRegistersRequest,
    decode_request_pdu,
    pack_bits,
    unpack_bits,
)
from clear_modbus.protocol.rtu import ModbusRTUFrame, crc16_modbus

CRC_PAYLOAD = bytes.fromhex("01 03 00 00 00 7D")

MBAP_HEADER = MBAPHeader(transaction_id=1, protocol_id=0, length=6, unit_id=1)
MBAP_HEADER_BYTES = bytes.fromhex("00 01 00 00 00 06 01")

TCP_FRAME = ModbusTCPFrame(
    transaction_id=1,
    unit_id=1,
    pdu=bytes.fromhex("03 00 00 00 02"),
)
TCP_FRAME_BYTES = bytes.fromhex("00 01 00 00 00 06 01 03 00 00 00 02")

READ_REGISTERS_REQUEST = ReadHoldingRegistersRequest(address=0, count=125)
READ_REGISTERS_RESPONSE = ReadRegistersResponse(
    function_code=0x03,
    values=list(range(125)),
)
READ_REGISTERS_RESPONSE_PAYLOAD = READ_REGISTERS_RESPONSE.encode()[1:]

WRITE_REGISTERS_REQUEST = WriteMultipleRegistersRequest(
    address=0,
    values=list(range(123)),
)
WRITE_REGISTERS_REQUEST_BYTES = WRITE_REGISTERS_REQUEST.encode()

BIT_VALUES = [index % 3 == 0 for index in range(1968)]
PACKED_BITS = pack_bits(BIT_VALUES)
WRITE_COILS_REQUEST = WriteMultipleCoilsRequest(address=0, values=BIT_VALUES)

RTU_FRAME = ModbusRTUFrame(unit_id=1, pdu=READ_REGISTERS_REQUEST.encode())
RTU_FRAME_BYTES = RTU_FRAME.encode()


def _bench_crc16_modbus() -> int:
    return crc16_modbus(CRC_PAYLOAD)


def _bench_mbap_header_encode() -> bytes:
    return MBAP_HEADER.encode()


def _bench_mbap_header_decode() -> MBAPHeader:
    return MBAPHeader.decode(MBAP_HEADER_BYTES)


def _bench_tcp_frame_encode() -> bytes:
    return TCP_FRAME.encode()


def _bench_tcp_frame_decode() -> ModbusTCPFrame:
    return ModbusTCPFrame.decode(TCP_FRAME_BYTES)


def _bench_read_registers_request_encode() -> bytes:
    return READ_REGISTERS_REQUEST.encode()


def _bench_read_registers_response_encode() -> bytes:
    return READ_REGISTERS_RESPONSE.encode()


def _bench_read_registers_response_decode() -> ReadRegistersResponse:
    return ReadRegistersResponse.decode(
        function_code=0x03,
        payload=READ_REGISTERS_RESPONSE_PAYLOAD,
    )


def _bench_write_registers_request_encode() -> bytes:
    return WRITE_REGISTERS_REQUEST.encode()


def _bench_write_registers_request_decode() -> RequestPDU:
    return decode_request_pdu(WRITE_REGISTERS_REQUEST_BYTES)


def _bench_pack_bits() -> bytes:
    return pack_bits(BIT_VALUES)


def _bench_unpack_bits() -> list[bool]:
    return unpack_bits(PACKED_BITS, len(BIT_VALUES))


def _bench_write_coils_request_encode() -> bytes:
    return WRITE_COILS_REQUEST.encode()


def _bench_rtu_frame_encode() -> bytes:
    return RTU_FRAME.encode()


def _bench_rtu_frame_decode() -> ModbusRTUFrame:
    return ModbusRTUFrame.decode(RTU_FRAME_BYTES)


def _main() -> None:
    runner = pyperf.Runner()
    runner.bench_func("crc16_modbus", _bench_crc16_modbus)
    runner.bench_func("mbap_header_encode", _bench_mbap_header_encode)
    runner.bench_func("mbap_header_decode", _bench_mbap_header_decode)
    runner.bench_func("tcp_frame_encode", _bench_tcp_frame_encode)
    runner.bench_func("tcp_frame_decode", _bench_tcp_frame_decode)
    runner.bench_func(
        "read_registers_request_encode",
        _bench_read_registers_request_encode,
    )
    runner.bench_func(
        "read_registers_response_encode",
        _bench_read_registers_response_encode,
    )
    runner.bench_func(
        "read_registers_response_decode",
        _bench_read_registers_response_decode,
    )
    runner.bench_func(
        "write_registers_request_encode",
        _bench_write_registers_request_encode,
    )
    runner.bench_func(
        "write_registers_request_decode",
        _bench_write_registers_request_decode,
    )
    runner.bench_func("pack_bits", _bench_pack_bits)
    runner.bench_func("unpack_bits", _bench_unpack_bits)
    runner.bench_func("write_coils_request_encode", _bench_write_coils_request_encode)
    runner.bench_func("rtu_frame_encode", _bench_rtu_frame_encode)
    runner.bench_func("rtu_frame_decode", _bench_rtu_frame_decode)


if __name__ == "__main__":
    _main()
