from modbus.transport import TCPTransport
from types import TracebackType
from typing import Self

from modbus.constants import DEFAULT_MODBUS_TCP_PORT, DEFAULT_UNIT_ID
from modbus.protocol.codec import ModbusTCPCodec
from modbus.protocol.mbap import MBAPHeader
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


class ModbusTcpClient:
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
        self.transport = TCPTransport(host=self.host, port=self.port, timeout=self.timeout)
        self.codec = ModbusTCPCodec()
        self._transaction_id = 1

    def _next_transaction_id(self) -> int:
        transaction_id = self._transaction_id

        self._transaction_id += 1
        if self._transaction_id > 0xFFFF:
            self._transaction_id = 1
        return transaction_id

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

    async def execute(self, request: RequestPDU, unit_id: int | None = None) -> ResponsePDU:
        if unit_id is None:
            unit_id = self.unit_id
        next_transaction_id = self._next_transaction_id()
        payload = self.codec.encode_request(request=request, transaction_id=next_transaction_id, unit_id=unit_id)
        await self.transport.send(payload)
        data = await self.transport.receive(7)
        header = MBAPHeader.decode(data=data)
        pdu = await self.transport.receive(header.length - 1)
        data = header.encode() + pdu
        response = self.codec.decode_response(data=data, request=request, expected_transaction_id=next_transaction_id, expected_unit_id=unit_id)
        return response

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
        response = await self.execute(request, unit_id)
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
        response = await self.execute(request, unit_id)
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
        response = await self.execute(request, unit_id)
        if not isinstance(response, WriteMultipleRegistersResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.count != len(values):
            raise ValueError()
        return response
