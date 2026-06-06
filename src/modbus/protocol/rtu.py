from dataclasses import dataclass

from modbus.protocol.functions import is_exception_function_code
from modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    RequestPDU,
    ResponsePDU,
    WriteMultipleRegistersRequest,
    WriteSingleRegisterRequest,
    decode_response_pdu,
)

MIN_RTU_FRAME_SIZE = 4
RTU_RESPONSE_PREFIX_SIZE = 2
RTU_EXCEPTION_RESPONSE_SIZE = 5
RTU_WRITE_REGISTER_RESPONSE_SIZE = 8


@dataclass(frozen=True)
class ModbusRTUFrame:
    unit_id: int
    pdu: bytes

    def encode(self) -> bytes:
        data = bytes([self.unit_id]) + self.pdu
        crc = crc16_modbus(data)
        return data + crc.to_bytes(2, "little")

    @classmethod
    def decode(cls, data: bytes) -> "ModbusRTUFrame":
        if len(data) < MIN_RTU_FRAME_SIZE:
            raise ValueError("RTU frame must include unit id, PDU, and CRC")

        message = data[:-2]
        received_crc = int.from_bytes(data[-2:], "little")
        expected_crc = crc16_modbus(message)
        if received_crc != expected_crc:
            raise ValueError("RTU frame CRC does not match payload")

        unit_id = message[0]
        pdu = message[1:]
        if len(pdu) == 0:
            raise ValueError("RTU frame PDU is empty")

        return cls(unit_id=unit_id, pdu=pdu)


class ModbusRTUCodec:
    def encode_request(self, request: RequestPDU, *, unit_id: int) -> bytes:
        frame = ModbusRTUFrame(unit_id=unit_id, pdu=request.encode())
        return frame.encode()

    def decode_response(
        self,
        data: bytes,
        request: RequestPDU,
        *,
        expected_unit_id: int,
    ) -> ResponsePDU:
        frame = ModbusRTUFrame.decode(data)
        if frame.unit_id != expected_unit_id:
            raise ValueError("RTU response unit id does not match request")
        return decode_response_pdu(data=frame.pdu, request=request)


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def encode_rtu_frame(frame: ModbusRTUFrame) -> bytes:
    return frame.encode()


def decode_rtu_frame(data: bytes) -> ModbusRTUFrame:
    return ModbusRTUFrame.decode(data)


def fixed_rtu_response_size(request: RequestPDU) -> int | None:
    if isinstance(request, (WriteSingleRegisterRequest, WriteMultipleRegistersRequest)):
        return RTU_WRITE_REGISTER_RESPONSE_SIZE
    if isinstance(request, (ReadHoldingRegistersRequest, ReadInputRegistersRequest)):
        return None
    return None


def rtu_response_size_from_prefix(prefix: bytes, request: RequestPDU) -> int | None:
    if len(prefix) != RTU_RESPONSE_PREFIX_SIZE:
        raise ValueError("RTU response prefix must be unit id plus function code")

    function_code = prefix[1]
    if is_exception_function_code(function_code):
        return RTU_EXCEPTION_RESPONSE_SIZE

    return fixed_rtu_response_size(request)


def rtu_read_register_response_size(byte_count: int) -> int:
    if byte_count < 0:
        raise ValueError("RTU read-register byte count must be non-negative")
    if byte_count % 2 != 0:
        raise ValueError("RTU read-register byte count must be even")
    return RTU_RESPONSE_PREFIX_SIZE + 1 + byte_count + 2
