import asyncio
from types import TracebackType
from typing import Self

from modbus import (
    ExceptionResponse,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)
from modbus.constants import DEFAULT_MODBUS_TCP_PORT, MODBUS_TCP_PROTOCOL_ID
from modbus.datastore import InvalidAddressError, MemoryDataStore, ReadOnlyDataBlockError
from modbus.datastore.base import ModbusDataStore
from modbus.datastore.errors import InvalidValueError
from modbus.exceptions import ModbusPDUError
from modbus.protocol.functions import ExceptionCode, FunctionCode
from modbus.protocol.mbap import MBAPHeader, ModbusTCPFrame
from modbus.protocol.pdu import RequestPDU, ResponsePDU


class ModbusTcpServer:
    host: str
    port: int
    datastore: ModbusDataStore

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_MODBUS_TCP_PORT,
        datastore: ModbusDataStore | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.datastore = datastore if datastore is not None else MemoryDataStore()
        self._server: asyncio.Server | None = None

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.stop()

    async def start(self) -> None:
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
                    request = _decode_request_pdu(pdu)
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
        if self._server is None:
            return

        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def handle_request(self, request: RequestPDU) -> ResponsePDU:
        try:
            match request:
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
                case WriteSingleRegisterRequest(address=address, value=value):
                    self.datastore.set_holding_registers(address, [value])
                    return WriteSingleRegisterResponse(
                        function_code=request.function_code, address=address, value=value
                    )
                case WriteMultipleRegistersRequest(address=address, values=values):
                    self.datastore.set_holding_registers(address, values)
                    return WriteMultipleRegistersResponse(
                        function_code=request.function_code,
                        address=address,
                        count=len(values),
                    )
                case _:
                    # TODO: Consider returning ExceptionResponse(..., ILLEGAL_FUNCTION)
                    # so unsupported PDUs are encoded as Modbus exception responses
                    # instead of escaping as Python errors.
                    raise ModbusPDUError(
                        f"Unsupported request type: {type(request).__name__}"
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


def _decode_request_pdu(data: bytes) -> RequestPDU:
    if len(data) == 0:
        raise ValueError("PDU is empty")

    function_code = data[0]
    payload = data[1:]

    if function_code in (
        FunctionCode.READ_HOLDING_REGISTERS,
        FunctionCode.READ_INPUT_REGISTERS,
    ):
        if len(payload) != 4:
            raise ValueError("read register request payload must be 4 bytes")
        address = int.from_bytes(payload[0:2], "big")
        count = int.from_bytes(payload[2:4], "big")
        if function_code == FunctionCode.READ_HOLDING_REGISTERS:
            return ReadHoldingRegistersRequest(address=address, count=count)
        return ReadInputRegistersRequest(address=address, count=count)

    if function_code == FunctionCode.WRITE_SINGLE_REGISTER:
        if len(payload) != 4:
            raise ValueError("write single register request payload must be 4 bytes")
        address = int.from_bytes(payload[0:2], "big")
        value = int.from_bytes(payload[2:4], "big")
        return WriteSingleRegisterRequest(address=address, value=value)

    if function_code == FunctionCode.WRITE_MULTIPLE_REGISTERS:
        if len(payload) < 5:
            raise ValueError("write multiple registers request payload is too short")

        address = int.from_bytes(payload[0:2], "big")
        count = int.from_bytes(payload[2:4], "big")
        byte_count = payload[4]
        register_bytes = payload[5:]

        if byte_count != len(register_bytes):
            raise ValueError("register byte count does not match payload length")
        if byte_count % 2 != 0:
            raise ValueError("register byte count must be even")
        if count != byte_count // 2:
            raise ValueError("register count does not match byte count")

        values = [
            int.from_bytes(register_bytes[i : i + 2], "big")
            for i in range(0, len(register_bytes), 2)
        ]
        return WriteMultipleRegistersRequest(address=address, values=values)

    raise ModbusPDUError(f"Unsupported function code: {function_code}")


def _encode_exception_response(data: bytes, exception_code: ExceptionCode) -> bytes:
    function_code = data[0] if data else 0
    response = ExceptionResponse(
        function_code=function_code,
        exception_code=exception_code,
    )
    return response.encode()
