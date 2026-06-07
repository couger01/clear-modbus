"""Modbus TCP MBAP header and frame helpers."""

from dataclasses import dataclass

from modbus.constants import MODBUS_TCP_PROTOCOL_ID
from modbus.exceptions import ModbusFrameError


@dataclass(frozen=True)
class MBAPHeader:
    """Modbus Application Protocol header.

    Parameters
    ----------
    transaction_id : int
        Transaction identifier used to match responses to requests.
    protocol_id : int
        Protocol identifier. Modbus TCP uses ``0``.
    length : int
        Number of following bytes, including the unit id and PDU.
    unit_id : int
        Modbus unit identifier.

    Attributes
    ----------
    transaction_id : int
        Transaction identifier used to match responses to requests.
    protocol_id : int
        Protocol identifier. Modbus TCP uses ``0``.
    length : int
        Number of following bytes, including the unit id and PDU.
    unit_id : int
        Modbus unit identifier.

    """

    transaction_id: int
    protocol_id: int
    length: int
    unit_id: int

    def encode(self) -> bytes:
        """Encode the header as seven MBAP bytes.

        Returns
        -------
        bytes
            Encoded MBAP header.

        """
        header = bytearray()
        header += self.transaction_id.to_bytes(2, "big")
        header += self.protocol_id.to_bytes(2, "big")
        header += self.length.to_bytes(2, "big")
        header.append(self.unit_id)
        return bytes(header)

    @classmethod
    def decode(cls, data: bytes) -> "MBAPHeader":
        """Decode a seven-byte MBAP header.

        Parameters
        ----------
        data : bytes
            Header bytes.

        Returns
        -------
        MBAPHeader
            Decoded header.

        Raises
        ------
        ModbusFrameError
            If ``data`` is not exactly seven bytes.

        """
        if len(data) != 7:
            raise ModbusFrameError("MBAP header must be exactly 7 bytes.")
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
    """Modbus TCP ADU frame.

    Parameters
    ----------
    transaction_id : int
        Transaction identifier.
    unit_id : int
        Modbus unit identifier.
    pdu : bytes
        Encoded PDU bytes.
    protocol_id : int, optional
        MBAP protocol identifier.

    Attributes
    ----------
    transaction_id : int
        Transaction identifier.
    unit_id : int
        Modbus unit identifier.
    pdu : bytes
        Encoded PDU bytes.
    protocol_id : int
        MBAP protocol identifier.

    """

    transaction_id: int
    unit_id: int
    pdu: bytes
    protocol_id: int = MODBUS_TCP_PROTOCOL_ID

    def encode(self) -> bytes:
        """Encode the MBAP header and PDU.

        Returns
        -------
        bytes
            Encoded Modbus TCP frame.

        """
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
        """Decode and validate a Modbus TCP frame.

        Parameters
        ----------
        data : bytes
            Complete Modbus TCP frame.

        Returns
        -------
        ModbusTCPFrame
            Decoded frame.

        Raises
        ------
        ModbusFrameError
            If the frame is missing, malformed, or has an invalid MBAP length.

        """
        if data is None:
            raise ModbusFrameError("TCP frame data is required.")
        header = MBAPHeader.decode(data[0:7])
        pdu = data[7:]
        if header.protocol_id != MODBUS_TCP_PROTOCOL_ID:
            raise ModbusFrameError("MBAP protocol id must be 0 for Modbus TCP.")
        if header.length != 1 + len(pdu):
            raise ModbusFrameError("MBAP length does not match PDU length.")

        return cls(
            transaction_id=header.transaction_id,
            unit_id=header.unit_id,
            pdu=pdu,
            protocol_id=header.protocol_id,
        )
