from types import TracebackType
from typing import Self

from modbus.constants import DEFAULT_UNIT_ID
from modbus.protocol.pdu import (
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    RequestPDU,
    ResponsePDU,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from modbus.protocol.rtu import (
    RTU_RESPONSE_PREFIX_SIZE,
    ModbusRTUCodec,
    rtu_read_register_response_size,
    rtu_response_size_from_prefix,
)
from modbus.transport import SerialTransport, Transport


class ModbusRtuClient:
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
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def connect(self) -> None:
        await self.transport.connect()

    async def close(self) -> None:
        await self.transport.close()

    async def execute(
        self, request: RequestPDU, unit_id: int | None = None
    ) -> ResponsePDU:
        if unit_id is None:
            unit_id = self.unit_id

        payload = self.codec.encode_request(request=request, unit_id=unit_id)
        await self.transport.send(payload)

        prefix = await self.transport.receive(RTU_RESPONSE_PREFIX_SIZE)
        response_size = rtu_response_size_from_prefix(prefix, request)
        if response_size is None:
            byte_count_data = await self.transport.receive(1)
            response_size = rtu_read_register_response_size(byte_count_data[0])
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

    async def read_holding_registers(
        self,
        address: int,
        count: int,
        unit_id: int | None = None,
    ) -> ReadRegistersResponse:
        request = ReadHoldingRegistersRequest(address=address, count=count)
        response = await self.execute(request, unit_id=unit_id)
        if not isinstance(response, ReadRegistersResponse):
            raise ValueError()
        return response

    async def read_input_registers(
        self,
        address: int,
        count: int,
        unit_id: int | None = None,
    ) -> ReadRegistersResponse:
        request = ReadInputRegistersRequest(address=address, count=count)
        response = await self.execute(request, unit_id=unit_id)
        if not isinstance(response, ReadRegistersResponse):
            raise ValueError()
        return response

    async def write_single_register(
        self,
        address: int,
        value: int,
        unit_id: int | None = None,
    ) -> WriteSingleRegisterResponse:
        request = WriteSingleRegisterRequest(address=address, value=value)
        response = await self.execute(request, unit_id=unit_id)
        if not isinstance(response, WriteSingleRegisterResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.value != value:
            raise ValueError()
        return response

    async def write_multiple_registers(
        self,
        address: int,
        values: list[int],
        unit_id: int | None = None,
    ) -> WriteMultipleRegistersResponse:
        request = WriteMultipleRegistersRequest(address=address, values=values)
        response = await self.execute(request, unit_id=unit_id)
        if not isinstance(response, WriteMultipleRegistersResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.count != len(values):
            raise ValueError()
        return response
