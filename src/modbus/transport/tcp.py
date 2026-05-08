from modbus.exceptions import ModbusConnectionError, ModbusTransportError, ModbusTimeoutError
import asyncio
from types import TracebackType
from typing import Self

from modbus.constants import DEFAULT_MODBUS_TCP_PORT


class TCPTransport:
    host: str
    port: int
    timeout: float

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_MODBUS_TCP_PORT,
        timeout: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.stream_writer = None
        self.stream_reader = None

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
        if self.stream_writer is not None:
            await self.close()
        try:
            async with asyncio.timeout(self.timeout):
                self.stream_reader, self.stream_writer =await asyncio.open_connection(host=self.host, port=self.port)
        except TimeoutError as e:
            raise ModbusTimeoutError(e)
        except Exception as e:
            raise ModbusConnectionError(e)

    async def close(self) -> None:
        if self.stream_writer is None:
            return
        writer = self.stream_writer
        self.stream_writer = None
        self.stream_reader = None
        writer.close()
        await writer.wait_closed()

    async def send(self, data: bytes) -> None:
        if self.stream_writer is None:
            raise ModbusConnectionError()
        try:
            self.stream_writer.write(data)
            async with asyncio.timeout(self.timeout):
                await self.stream_writer.drain()
        except TimeoutError as e:
            raise ModbusTimeoutError(e)
        except Exception as e:
            raise ModbusTransportError(e)

    async def receive(self, size: int) -> bytes:
        if self.stream_reader is None:
            raise ModbusConnectionError()
        if size <= 0:
            raise ValueError()
        try:
            async with asyncio.timeout(self.timeout):
                reply = await self.stream_reader.readexactly(size)
                return reply
        except TimeoutError as e:
            raise ModbusTimeoutError(e)
        except asyncio.IncompleteReadError as e:
            raise ModbusTransportError(e)
        except ConnectionError as e:
            raise ModbusConnectionError(e)
