"""Codec for Modbus TCP request and response frames."""

from clear_modbus.exceptions import ModbusResponseMismatchError
from clear_modbus.protocol.mbap import ModbusTCPFrame
from clear_modbus.protocol.pdu import RequestPDU, ResponsePDU, decode_response_pdu

__all__ = ["ModbusTCPCodec", "decode_tcp_frame", "encode_tcp_frame"]


class ModbusTCPCodec:
    """Encode and decode Modbus TCP frames."""

    def encode_request(
        self,
        request: RequestPDU,
        *,
        transaction_id: int,
        unit_id: int,
    ) -> bytes:
        """Encode a request PDU into a Modbus TCP frame.

        Parameters
        ----------
        request : RequestPDU
            Request PDU to encode.
        transaction_id : int
            Transaction identifier to place in the MBAP header.
        unit_id : int
            Unit identifier to place in the MBAP header.

        Returns
        -------
        bytes
            Encoded Modbus TCP frame.

        """
        pdu = request.encode()

        frame = ModbusTCPFrame(transaction_id=transaction_id, unit_id=unit_id, pdu=pdu)

        return frame.encode()

    def decode_response(
        self,
        data: bytes,
        request: RequestPDU,
        *,
        expected_transaction_id: int,
        expected_unit_id: int,
    ) -> ResponsePDU:
        """Decode a Modbus TCP response frame.

        Parameters
        ----------
        data : bytes
            Complete response frame.
        request : RequestPDU
            Original request PDU used to select the response decoder.
        expected_transaction_id : int
            Expected MBAP transaction identifier.
        expected_unit_id : int
            Expected MBAP unit identifier.

        Returns
        -------
        ResponsePDU
            Decoded response PDU.

        Raises
        ------
        ModbusResponseMismatchError
            If the transaction id or unit id does not match the request
            context.

        """
        frame = ModbusTCPFrame.decode(data)
        if frame.transaction_id != expected_transaction_id:
            raise ModbusResponseMismatchError(
                "Response transaction id does not match request."
            )
        if frame.unit_id != expected_unit_id:
            raise ModbusResponseMismatchError(
                "Response unit id does not match request."
            )
        return decode_response_pdu(data=frame.pdu, request=request)


def encode_tcp_frame(frame: ModbusTCPFrame) -> bytes:
    """Encode a Modbus TCP frame.

    Parameters
    ----------
    frame : ModbusTCPFrame
        Frame to encode.

    Returns
    -------
    bytes
        Encoded frame bytes.

    """
    return frame.encode()


def decode_tcp_frame(data: bytes) -> ModbusTCPFrame:
    """Decode a Modbus TCP frame.

    Parameters
    ----------
    data : bytes
        Frame bytes to decode.

    Returns
    -------
    ModbusTCPFrame
        Decoded frame.

    """
    return ModbusTCPFrame.decode(data)
