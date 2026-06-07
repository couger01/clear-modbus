"""Async Modbus TCP client."""

from types import TracebackType
from typing import Self

from clear_modbus.client_helpers import ModbusClientOperations
from clear_modbus.constants import DEFAULT_MODBUS_TCP_PORT, DEFAULT_UNIT_ID
from clear_modbus.protocol.codec import ModbusTCPCodec
from clear_modbus.protocol.mbap import MBAPHeader
from clear_modbus.protocol.pdu import RequestPDU, ResponsePDU
from clear_modbus.transport import TCPTransport

__all__ = ["ModbusTcpClient"]


class ModbusTcpClient(ModbusClientOperations):
    """Client for Modbus TCP servers.

    Parameters
    ----------
    host : str
        Server hostname or IP address.
    port : int, optional
        TCP port.
    unit_id : int
        Default Modbus unit identifier.
    timeout : float
        Timeout in seconds for transport operations.

    Attributes
    ----------
    host : str
        Server hostname or IP address.
    port : int
        TCP port.
    unit_id : int
        Default Modbus unit identifier.
    timeout : float
        Timeout in seconds for transport operations.

    """

    host: str
    port: int
    unit_id: int
    timeout: float

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_MODBUS_TCP_PORT,
        unit_id: int = DEFAULT_UNIT_ID,
        timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.transport = TCPTransport(
            host=self.host, port=self.port, timeout=self.timeout
        )
        self.codec = ModbusTCPCodec()
        self._transaction_id = 1

    def _next_transaction_id(self) -> int:
        transaction_id = self._transaction_id

        self._transaction_id += 1
        if self._transaction_id > 0xFFFF:
            self._transaction_id = 1
        return transaction_id

    async def __aenter__(self) -> Self:
        """Connect and return this client.

        Returns
        -------
        Self
            Connected client.

        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the client when leaving an async context."""
        await self.close()

    async def connect(self) -> None:
        """Open the underlying TCP transport."""
        await self.transport.connect()

    async def close(self) -> None:
        """Close the underlying TCP transport."""
        await self.transport.close()

    async def execute(
        self, request: RequestPDU, unit_id: int | None = None
    ) -> ResponsePDU:
        """Send a request PDU and decode the response PDU.

        Parameters
        ----------
        request : RequestPDU
            Request PDU to encode and send.
        unit_id : int | None
            Unit identifier override. Defaults to the client's configured
            ``unit_id``.

        Returns
        -------
        ResponsePDU
            Decoded response PDU.

        """
        if unit_id is None:
            unit_id = self.unit_id
        next_transaction_id = self._next_transaction_id()
        payload = self.codec.encode_request(
            request=request, transaction_id=next_transaction_id, unit_id=unit_id
        )
        await self.transport.send(payload)
        data = await self.transport.receive(7)
        header = MBAPHeader.decode(data=data)
        pdu = await self.transport.receive(header.length - 1)
        data = header.encode() + pdu
        response = self.codec.decode_response(
            data=data,
            request=request,
            expected_transaction_id=next_transaction_id,
            expected_unit_id=unit_id,
        )
        return response
