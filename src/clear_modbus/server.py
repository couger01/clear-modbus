"""Async Modbus TCP server backed by a datastore."""

import asyncio
from types import TracebackType
from typing import Self

from clear_modbus import (
    DeviceIdentificationConformityLevel,
    DeviceIdentificationObject,
    ExceptionResponse,
    MaskWriteRegisterRequest,
    MaskWriteRegisterResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDeviceIdentificationRequest,
    ReadDeviceIdentificationResponse,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    ReadWriteMultipleRegistersRequest,
    WriteMultipleCoilsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleCoilRequest,
    WriteSingleCoilResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from clear_modbus.constants import DEFAULT_MODBUS_TCP_PORT, MODBUS_TCP_PROTOCOL_ID
from clear_modbus.datastore import (
    InvalidAddressError,
    MemoryDataStore,
    ReadOnlyDataBlockError,
)
from clear_modbus.datastore.base import ModbusDataStore
from clear_modbus.datastore.errors import InvalidValueError
from clear_modbus.exceptions import ModbusPDUError
from clear_modbus.protocol.functions import ExceptionCode
from clear_modbus.protocol.mbap import MBAPHeader, ModbusTCPFrame
from clear_modbus.protocol.pdu import RequestPDU, ResponsePDU, decode_request_pdu

__all__ = ["ModbusTcpServer"]


class ModbusTcpServer:
    """Modbus TCP server.

    Parameters
    ----------
    host : str
        Interface address to bind.
    port : int
        TCP port to bind.
    datastore : ModbusDataStore | None
        Datastore used to service requests.

    Attributes
    ----------
    host : str
        Interface address to bind.
    port : int
        TCP port to bind.
    datastore : ModbusDataStore
        Datastore used to service requests.

    """

    host: str
    port: int
    datastore: ModbusDataStore

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_MODBUS_TCP_PORT,
        datastore: ModbusDataStore | None = None,
        device_identification: dict[int, bytes | str] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.datastore = datastore if datastore is not None else MemoryDataStore()
        self.device_identification = _normalize_device_identification(
            device_identification if device_identification is not None else {}
        )
        self._server: asyncio.Server | None = None

    async def __aenter__(self) -> Self:
        """Start the server and return this instance.

        Returns
        -------
        Self
            Running server.

        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop the server when leaving an async context."""
        await self.stop()

    async def start(self) -> None:
        """Bind the TCP socket and begin accepting clients."""
        if self._server is not None:
            return
        self._server = await asyncio.start_server(
            self._handle_client, host=self.host, port=self.port
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                try:
                    header_data = await reader.readexactly(7)
                except asyncio.IncompleteReadError:
                    break

                try:
                    header = MBAPHeader.decode(header_data)
                    if header.protocol_id != MODBUS_TCP_PROTOCOL_ID:
                        raise ValueError("unsupported MBAP protocol id")
                    if header.length < 1:
                        raise ValueError("MBAP length must include unit id")
                except ValueError:
                    break

                try:
                    pdu = await reader.readexactly(header.length - 1)
                    request = decode_request_pdu(pdu)
                    response = await self.handle_request(request)
                    response_pdu = response.encode()
                except asyncio.IncompleteReadError:
                    break
                except ModbusPDUError:
                    response_pdu = _encode_exception_response(
                        pdu,
                        ExceptionCode.ILLEGAL_FUNCTION,
                    )
                except ValueError:
                    response_pdu = _encode_exception_response(
                        pdu,
                        ExceptionCode.ILLEGAL_DATA_VALUE,
                    )

                response_frame = ModbusTCPFrame(
                    transaction_id=header.transaction_id,
                    unit_id=header.unit_id,
                    pdu=response_pdu,
                    protocol_id=header.protocol_id,
                )
                writer.write(response_frame.encode())
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def stop(self) -> None:
        """Stop accepting clients and close the server socket."""
        if self._server is None:
            return

        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def handle_request(self, request: RequestPDU) -> ResponsePDU:
        """Handle one decoded request PDU.

        Parameters
        ----------
        request : RequestPDU
            Decoded request PDU.

        Returns
        -------
        ResponsePDU
            Normal response PDU or exception response PDU.

        """
        try:
            match request:
                case ReadCoilsRequest(address=address, count=count):
                    values = self.datastore.get_coils(address, count)
                    return ReadBitsResponse(
                        function_code=request.function_code, values=values
                    )
                case ReadDiscreteInputsRequest(address=address, count=count):
                    values = self.datastore.get_discrete_inputs(address, count)
                    return ReadBitsResponse(
                        function_code=request.function_code, values=values
                    )
                case ReadHoldingRegistersRequest(address=address, count=count):
                    values = self.datastore.get_holding_registers(address, count)
                    return ReadRegistersResponse(
                        function_code=request.function_code, values=values
                    )
                case ReadInputRegistersRequest(address=address, count=count):
                    values = self.datastore.get_input_registers(address, count)
                    return ReadRegistersResponse(
                        function_code=request.function_code, values=values
                    )
                case WriteSingleCoilRequest(address=address, value=value):
                    self.datastore.set_coils(address, [value])
                    return WriteSingleCoilResponse(
                        function_code=request.function_code,
                        address=address,
                        value=value,
                    )
                case WriteSingleRegisterRequest(address=address, value=value):
                    self.datastore.set_holding_registers(address, [value])
                    return WriteSingleRegisterResponse(
                        function_code=request.function_code,
                        address=address,
                        value=value,
                    )
                case WriteMultipleCoilsRequest(address=address, values=values):
                    self.datastore.set_coils(address, values)
                    return WriteMultipleCoilsResponse(
                        function_code=request.function_code,
                        address=address,
                        count=len(values),
                    )
                case WriteMultipleRegistersRequest(address=address, values=values):
                    self.datastore.set_holding_registers(address, values)
                    return WriteMultipleRegistersResponse(
                        function_code=request.function_code,
                        address=address,
                        count=len(values),
                    )
                case MaskWriteRegisterRequest(
                    address=address,
                    and_mask=and_mask,
                    or_mask=or_mask,
                ):
                    value = self.datastore.get_holding_registers(address, 1)[0]
                    masked_value = (value & and_mask) | (or_mask & (~and_mask & 0xFFFF))
                    self.datastore.set_holding_registers(address, [masked_value])
                    return MaskWriteRegisterResponse(
                        function_code=request.function_code,
                        address=address,
                        and_mask=and_mask,
                        or_mask=or_mask,
                    )
                case ReadWriteMultipleRegistersRequest(
                    read_address=read_address,
                    read_count=read_count,
                    write_address=write_address,
                    values=values,
                ):
                    self.datastore.get_holding_registers(read_address, read_count)
                    self.datastore.set_holding_registers(write_address, values)
                    values = self.datastore.get_holding_registers(
                        read_address, read_count
                    )
                    return ReadRegistersResponse(
                        function_code=request.function_code,
                        values=values,
                    )
                case ReadDeviceIdentificationRequest():
                    return _read_device_identification(
                        request=request,
                        objects=self.device_identification,
                    )
                case _:
                    return ExceptionResponse(
                        function_code=request.function_code,
                        exception_code=ExceptionCode.ILLEGAL_FUNCTION,
                    )
        except (InvalidAddressError, ReadOnlyDataBlockError):
            return ExceptionResponse(
                function_code=request.function_code,
                exception_code=ExceptionCode.ILLEGAL_DATA_ADDRESS,
            )
        except InvalidValueError:
            return ExceptionResponse(
                function_code=request.function_code,
                exception_code=ExceptionCode.ILLEGAL_DATA_VALUE,
            )


def _encode_exception_response(data: bytes, exception_code: ExceptionCode) -> bytes:
    function_code = data[0] if data else 0
    response = ExceptionResponse(
        function_code=function_code,
        exception_code=exception_code,
    )
    return response.encode()


def _normalize_device_identification(
    objects: dict[int, bytes | str],
) -> dict[int, bytes]:
    normalized: dict[int, bytes] = {}
    for object_id, value in objects.items():
        if isinstance(value, str):
            encoded_value = value.encode()
        else:
            encoded_value = bytes(value)
        normalized[object_id] = DeviceIdentificationObject(
            object_id=object_id,
            value=encoded_value,
        ).value
    return normalized


def _read_device_identification(
    *,
    request: ReadDeviceIdentificationRequest,
    objects: dict[int, bytes],
) -> ReadDeviceIdentificationResponse | ExceptionResponse:
    if request.read_code == 4 and request.object_id not in objects:
        return ExceptionResponse(
            function_code=request.function_code,
            exception_code=ExceptionCode.ILLEGAL_DATA_ADDRESS,
        )

    selected = _select_device_identification_objects(
        read_code=request.read_code,
        start_object_id=request.object_id,
        objects=objects,
    )
    response_objects, more_follows, next_object_id = _fit_device_identification_objects(
        selected
    )
    return ReadDeviceIdentificationResponse(
        read_code=request.read_code,
        conformity_level=_device_identification_conformity_level(objects),
        more_follows=more_follows,
        next_object_id=next_object_id,
        objects=response_objects,
    )


def _select_device_identification_objects(
    *,
    read_code: int,
    start_object_id: int,
    objects: dict[int, bytes],
) -> list[DeviceIdentificationObject]:
    if read_code == 1:
        allowed_object_ids = range(0x00, 0x03)
    elif read_code == 2:
        allowed_object_ids = range(0x00, 0x80)
    elif read_code == 3:
        allowed_object_ids = range(0x00, 0x100)
    else:
        allowed_object_ids = range(start_object_id, start_object_id + 1)

    return [
        DeviceIdentificationObject(object_id=object_id, value=objects[object_id])
        for object_id in sorted(objects)
        if object_id in allowed_object_ids and object_id >= start_object_id
    ]


def _fit_device_identification_objects(
    objects: list[DeviceIdentificationObject],
) -> tuple[list[DeviceIdentificationObject], bool, int]:
    # Function code plus six-byte MEI response header.
    remaining = 253 - 7
    fitted: list[DeviceIdentificationObject] = []
    for item in objects:
        item_size = 2 + len(item.value)
        if item_size > remaining:
            return fitted, True, item.object_id
        fitted.append(item)
        remaining -= item_size
    return fitted, False, 0


def _device_identification_conformity_level(
    objects: dict[int, bytes],
) -> int:
    if any(object_id >= 0x80 for object_id in objects):
        return DeviceIdentificationConformityLevel.EXTENDED_INDIVIDUAL
    if any(object_id > 0x02 for object_id in objects):
        return DeviceIdentificationConformityLevel.REGULAR_INDIVIDUAL
    return DeviceIdentificationConformityLevel.BASIC_INDIVIDUAL
