import asyncio
from types import TracebackType
from typing import Self

from modbus.exceptions import ModbusConnectionError, ModbusTransportError, ModbusTimeoutError


class SerialTransport:
    port: str
    baudrate: int
    timeout: float

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1.0,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None

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
        if self.serial_connection is not None:
            await self.close()

        try:
            import serial
        except ImportError as exc:
            raise ModbusConnectionError(
                "SerialTransport requires pyserial to be installed."
            ) from exc

        try:
            self.serial_connection = await asyncio.to_thread(
                serial.Serial,
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        except Exception as exc:
            raise ModbusConnectionError(exc) from exc

    async def close(self) -> None:
        if self.serial_connection is None:
            return

        serial_connection = self.serial_connection
        self.serial_connection = None
        await asyncio.to_thread(serial_connection.close)

    async def send(self, data: bytes) -> None:
        if self.serial_connection is None:
            raise ModbusConnectionError()

        try:
            async with asyncio.timeout(self.timeout):
                written = await asyncio.to_thread(self.serial_connection.write, data)
                if written != len(data):
                    raise ModbusTransportError("Serial write did not write all bytes.")
        except TimeoutError as exc:
            raise ModbusTimeoutError(exc) from exc
        except ModbusTransportError:
            raise
        except Exception as exc:
            raise ModbusTransportError(exc) from exc

    async def receive(self, size: int) -> bytes:
        if self.serial_connection is None:
            raise ModbusConnectionError()
        if size <= 0:
            raise ValueError()

        try:
            async with asyncio.timeout(self.timeout):
                data = await asyncio.to_thread(self.serial_connection.read, size)
        except TimeoutError as exc:
            raise ModbusTimeoutError(exc) from exc
        except Exception as exc:
            raise ModbusTransportError(exc) from exc

        if len(data) != size:
            raise ModbusTransportError("Serial read returned fewer bytes than requested.")
        return data
