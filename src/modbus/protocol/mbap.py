from dataclasses import dataclass

from modbus.constants import MODBUS_TCP_PROTOCOL_ID


@dataclass(frozen=True)
class MBAPHeader:
    transaction_id: int
    protocol_id: int
    length: int
    unit_id: int

    def encode(self) -> bytes:
        header = bytearray()
        header += self.transaction_id.to_bytes(2, "big")
        header += self.protocol_id.to_bytes(2, "big")
        header += self.length.to_bytes(2, "big")
        header.append(self.unit_id)
        return bytes(header)

    @classmethod
    def decode(cls, data: bytes) -> "MBAPHeader":
        if len(data) != 7:
            raise ValueError()
        transaction_id = int.from_bytes(data[0:2], "big")
        protocol_id = int.from_bytes(data[2:4], "big")
        length = int.from_bytes(data[4:6], "big")
        unit_id = data[6]
        return cls(
            transaction_id=transaction_id,
            protocol_id=protocol_id,
            length=length,
            unit_id=unit_id,
        )


@dataclass(frozen=True)
class ModbusTCPFrame:
    transaction_id: int
    unit_id: int
    pdu: bytes
    protocol_id: int = MODBUS_TCP_PROTOCOL_ID

    def encode(self) -> bytes:
        length = 1 + len(self.pdu)
        header = MBAPHeader(
            transaction_id=self.transaction_id,
            unit_id=self.unit_id,
            length=length,
            protocol_id=self.protocol_id,
        )
        frame = bytearray()
        frame += header.encode()
        frame += self.pdu
        return bytes(frame)

    @classmethod
    def decode(cls, data: bytes) -> "ModbusTCPFrame":
        if data is None:
            raise ValueError()
        header = MBAPHeader.decode(data[0:7])
        pdu = data[7:]
        if header.protocol_id != MODBUS_TCP_PROTOCOL_ID:
            raise ValueError()
        if header.length != 1 + len(pdu):
            raise ValueError()

        return cls(
            transaction_id=header.transaction_id,
            unit_id=header.unit_id,
            pdu=pdu,
            protocol_id=header.protocol_id,
        )
