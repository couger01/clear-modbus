"""Modbus RTU frame, CRC, and response-size helpers."""

from dataclasses import dataclass

from clear_modbus.exceptions import (
    ModbusCRCError,
    ModbusFrameError,
    ModbusResponseMismatchError,
)
from clear_modbus.protocol.functions import is_exception_function_code
from clear_modbus.protocol.pdu import (
    ReadCoilsRequest,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    RequestPDU,
    ResponsePDU,
    WriteMultipleCoilsRequest,
    WriteMultipleRegistersRequest,
    WriteSingleCoilRequest,
    WriteSingleRegisterRequest,
    decode_response_pdu,
)

MIN_RTU_FRAME_SIZE = 4
RTU_RESPONSE_PREFIX_SIZE = 2
RTU_EXCEPTION_RESPONSE_SIZE = 5
RTU_WRITE_REGISTER_RESPONSE_SIZE = 8

__all__ = [
    "ModbusRTUCodec",
    "ModbusRTUFrame",
    "crc16_modbus",
    "decode_rtu_frame",
    "encode_rtu_frame",
    "fixed_rtu_response_size",
    "rtu_byte_count_response_size",
    "rtu_read_register_response_size",
    "rtu_response_size_from_prefix",
]


@dataclass(frozen=True)
class ModbusRTUFrame:
    """Modbus RTU ADU frame.

    Parameters
    ----------
    unit_id : int
        Modbus unit identifier.
    pdu : bytes
        Encoded PDU bytes.

    Attributes
    ----------
    unit_id : int
        Modbus unit identifier.
    pdu : bytes
        Encoded PDU bytes.

    """

    unit_id: int
    pdu: bytes

    def encode(self) -> bytes:
        """Encode the unit id, PDU, and CRC.

        Returns
        -------
        bytes
            Encoded RTU frame.

        """
        data = bytes([self.unit_id]) + self.pdu
        crc = crc16_modbus(data)
        return data + crc.to_bytes(2, "little")

    @classmethod
    def decode(cls, data: bytes) -> "ModbusRTUFrame":
        """Decode and validate an RTU frame.

        Parameters
        ----------
        data : bytes
            Complete RTU frame, including CRC.

        Returns
        -------
        ModbusRTUFrame
            Decoded frame.

        Raises
        ------
        ModbusFrameError
            If the frame is too short or contains an empty PDU.
        ModbusCRCError
            If the frame CRC is invalid.

        """
        if len(data) < MIN_RTU_FRAME_SIZE:
            raise ModbusFrameError("RTU frame must include unit id, PDU, and CRC")

        message = data[:-2]
        received_crc = int.from_bytes(data[-2:], "little")
        expected_crc = crc16_modbus(message)
        if received_crc != expected_crc:
            raise ModbusCRCError("RTU frame CRC does not match payload")

        unit_id = message[0]
        pdu = message[1:]
        if len(pdu) == 0:
            raise ModbusFrameError("RTU frame PDU is empty")

        return cls(unit_id=unit_id, pdu=pdu)


class ModbusRTUCodec:
    """Encode and decode Modbus RTU frames."""

    def encode_request(self, request: RequestPDU, *, unit_id: int) -> bytes:
        """Encode a request PDU into an RTU frame.

        Parameters
        ----------
        request : RequestPDU
            Request PDU to encode.
        unit_id : int
            Unit identifier to place in the frame.

        Returns
        -------
        bytes
            Encoded RTU frame.

        """
        frame = ModbusRTUFrame(unit_id=unit_id, pdu=request.encode())
        return frame.encode()

    def decode_response(
        self,
        data: bytes,
        request: RequestPDU,
        *,
        expected_unit_id: int,
    ) -> ResponsePDU:
        """Decode an RTU response frame.

        Parameters
        ----------
        data : bytes
            Complete RTU response frame.
        request : RequestPDU
            Original request PDU used to select the response decoder.
        expected_unit_id : int
            Expected unit identifier.

        Returns
        -------
        ResponsePDU
            Decoded response PDU.

        Raises
        ------
        ModbusResponseMismatchError
            If the response unit id does not match ``expected_unit_id``.

        """
        frame = ModbusRTUFrame.decode(data)
        if frame.unit_id != expected_unit_id:
            raise ModbusResponseMismatchError(
                "RTU response unit id does not match request."
            )
        return decode_response_pdu(data=frame.pdu, request=request)


def crc16_modbus(data: bytes) -> int:
    """Calculate the Modbus RTU CRC-16 value.

    Parameters
    ----------
    data : bytes
        Bytes over which to calculate the CRC.

    Returns
    -------
    int
        CRC-16 value.

    """
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
    """Encode an RTU frame.

    Parameters
    ----------
    frame : ModbusRTUFrame
        Frame to encode.

    Returns
    -------
    bytes
        Encoded frame bytes.

    """
    return frame.encode()


def decode_rtu_frame(data: bytes) -> ModbusRTUFrame:
    """Decode an RTU frame.

    Parameters
    ----------
    data : bytes
        Frame bytes to decode.

    Returns
    -------
    ModbusRTUFrame
        Decoded frame.

    """
    return ModbusRTUFrame.decode(data)


def fixed_rtu_response_size(request: RequestPDU) -> int | None:
    """Return the fixed RTU response size for a request when known.

    Parameters
    ----------
    request : RequestPDU
        Request PDU.

    Returns
    -------
    int | None
        Fixed frame size, or ``None`` for byte-count responses.

    """
    if isinstance(
        request,
        (
            WriteSingleCoilRequest,
            WriteSingleRegisterRequest,
            WriteMultipleCoilsRequest,
            WriteMultipleRegistersRequest,
        ),
    ):
        return RTU_WRITE_REGISTER_RESPONSE_SIZE
    if isinstance(
        request,
        (
            ReadCoilsRequest,
            ReadDiscreteInputsRequest,
            ReadHoldingRegistersRequest,
            ReadInputRegistersRequest,
        ),
    ):
        return None
    return None


def rtu_response_size_from_prefix(prefix: bytes, request: RequestPDU) -> int | None:
    """Infer an RTU response size from the unit id and function code prefix.

    Parameters
    ----------
    prefix : bytes
        Two-byte response prefix containing unit id and function code.
    request : RequestPDU
        Original request PDU.

    Returns
    -------
    int | None
        Full RTU frame size, or ``None`` when a byte-count byte must be read.

    Raises
    ------
    ValueError
        If ``prefix`` is not exactly two bytes.

    """
    if len(prefix) != RTU_RESPONSE_PREFIX_SIZE:
        raise ValueError("RTU response prefix must be unit id plus function code")

    function_code = prefix[1]
    if is_exception_function_code(function_code):
        return RTU_EXCEPTION_RESPONSE_SIZE

    return fixed_rtu_response_size(request)


def rtu_read_register_response_size(byte_count: int) -> int:
    """Return an RTU read-register frame size from byte count.

    Parameters
    ----------
    byte_count : int
        Register byte count from the response PDU.

    Returns
    -------
    int
        Full RTU frame size.

    Raises
    ------
    ValueError
        If ``byte_count`` is negative or odd.

    """
    if byte_count < 0:
        raise ValueError("RTU read-register byte count must be non-negative")
    if byte_count % 2 != 0:
        raise ValueError("RTU read-register byte count must be even")
    return rtu_byte_count_response_size(byte_count)


def rtu_byte_count_response_size(byte_count: int) -> int:
    """Return an RTU frame size for byte-count response functions.

    Parameters
    ----------
    byte_count : int
        Byte count from the response PDU.

    Returns
    -------
    int
        Full RTU frame size.

    Raises
    ------
    ValueError
        If ``byte_count`` is negative.

    """
    if byte_count < 0:
        raise ValueError("RTU byte count must be non-negative")
    return RTU_RESPONSE_PREFIX_SIZE + 1 + byte_count + 2
