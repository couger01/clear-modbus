from modbus.protocol.mbap import ModbusTCPFrame
from modbus.protocol.pdu import RequestPDU, ResponsePDU, decode_response_pdu


class ModbusTCPCodec:
    def encode_request(
        self,
        request: RequestPDU,
        *,
        transaction_id: int,
        unit_id: int,
    ) -> bytes:
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
        frame = ModbusTCPFrame.decode(data)
        if frame.transaction_id != expected_transaction_id:
            raise ValueError()
        if frame.unit_id != expected_unit_id:
            raise ValueError()
        return decode_response_pdu(data=frame.pdu, request=request)


def encode_tcp_frame(frame: ModbusTCPFrame) -> bytes:
    return frame.encode()


def decode_tcp_frame(data: bytes) -> ModbusTCPFrame:
    return ModbusTCPFrame.decode(data)
