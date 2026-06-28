"""Async Modbus RTU client."""

from types import TracebackType
from typing import Self

from clear_modbus.client_helpers import ModbusClientOperations
from clear_modbus.constants import DEFAULT_UNIT_ID
from clear_modbus.protocol.pdu import (
    ReadDeviceIdentificationRequest,
    RequestPDU,
    ResponsePDU,
)
from clear_modbus.protocol.rtu import (
    RTU_RESPONSE_PREFIX_SIZE,
    ModbusRTUCodec,
    rtu_byte_count_response_size,
    rtu_response_size_from_prefix,
)
from clear_modbus.transport import SerialTransport, Transport

__all__ = ["ModbusRtuClient"]


class ModbusRtuClient(ModbusClientOperations):
    """Client for Modbus RTU serial devices.

    Parameters
    ----------
    port : str
        Serial device path.
    unit_id : int
        Default Modbus unit identifier.
    baudrate : int
        Serial baud rate.
    timeout : float
        Timeout in seconds for serial operations.
    transport : Transport | None
        Custom transport, primarily useful for tests.

    Attributes
    ----------
    port : str
        Serial device path.
    unit_id : int
        Default Modbus unit identifier.
    baudrate : int
        Serial baud rate.
    timeout : float
        Timeout in seconds for serial operations.

    """

    port: str
    unit_id: int
    baudrate: int
    timeout: float

    def __init__(
        self,
        port: str,
        unit_id: int = DEFAULT_UNIT_ID,
        baudrate: int = 9600,
        timeout: float = 1.0,
        transport: Transport | None = None,
    ) -> None:
        self.port = port
        self.unit_id = unit_id
        self.baudrate = baudrate
        self.timeout = timeout
        self.transport = (
            transport
            if transport is not None
            else SerialTransport(
                port=self.port, baudrate=self.baudrate, timeout=self.timeout
            )
        )
        self.codec = ModbusRTUCodec()

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
        """Open the underlying serial transport."""
        await self.transport.connect()

    async def close(self) -> None:
        """Close the underlying serial transport."""
        await self.transport.close()

    async def execute(
        self, request: RequestPDU, unit_id: int | None = None
    ) -> ResponsePDU:
        """Send a request PDU and decode the RTU response PDU.

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

        payload = self.codec.encode_request(request=request, unit_id=unit_id)
        await self.transport.send(payload)

        prefix = await self.transport.receive(RTU_RESPONSE_PREFIX_SIZE)
        response_size = rtu_response_size_from_prefix(prefix, request)
        if response_size is None and isinstance(
            request, ReadDeviceIdentificationRequest
        ):
            data = prefix + await self._receive_read_device_identification_response()
            return self.codec.decode_response(
                data=data,
                request=request,
                expected_unit_id=unit_id,
            )
        if response_size is None:
            byte_count_data = await self.transport.receive(1)
            response_size = rtu_byte_count_response_size(byte_count_data[0])
            remaining_size = response_size - RTU_RESPONSE_PREFIX_SIZE - 1
            data = (
                prefix + byte_count_data + await self.transport.receive(remaining_size)
            )
        else:
            remaining_size = response_size - RTU_RESPONSE_PREFIX_SIZE
            data = prefix + await self.transport.receive(remaining_size)

        return self.codec.decode_response(
            data=data,
            request=request,
            expected_unit_id=unit_id,
        )

    async def _receive_read_device_identification_response(self) -> bytes:
        """Read a variable-length Read Device Identification RTU response body.

        Returns
        -------
        bytes
            Response bytes after the unit id and function-code prefix.

        """
        header = await self.transport.receive(6)
        object_count = header[5]
        data = bytearray(header)
        for _ in range(object_count):
            object_header = await self.transport.receive(2)
            data.extend(object_header)
            value_length = object_header[1]
            if value_length:
                data.extend(await self.transport.receive(value_length))
        data.extend(await self.transport.receive(2))
        return bytes(data)

    @property
    def connected(self) -> bool:
        """Whether the underlying serial transport is connected."""
        return self.transport.connected
