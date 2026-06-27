"""Async serial transport for Modbus RTU connections."""

import asyncio
from functools import partial
from types import TracebackType
from typing import Self

from clear_modbus.exceptions import (
    ModbusConnectionError,
    ModbusTimeoutError,
    ModbusTransportError,
)

__all__ = ["SerialTransport"]


def _is_serial_timeout_error(exc: Exception) -> bool:
    try:
        import serial
    except ImportError:
        return False

    return isinstance(exc, serial.SerialTimeoutException)


class SerialTransport:
    """Asynchronous serial byte transport.

    Parameters
    ----------
    port : str
        Serial device path, such as ``"/dev/ttyUSB0"``.
    baudrate : int
        Serial baud rate.
    timeout : float
        Timeout in seconds for connect, send, and receive operations.

    Attributes
    ----------
    port : str
        Serial device path.
    baudrate : int
        Serial baud rate.
    timeout : float
        Timeout in seconds for connect, send, and receive operations.

    """

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
        """Open the serial connection and return this transport.

        Returns
        -------
        Self
            Connected transport.

        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the serial connection when leaving an async context."""
        await self.close()

    async def connect(self) -> None:
        """Open the configured serial port.

        Raises
        ------
        ModbusConnectionError
            If pyserial is unavailable or the serial port cannot be opened.

        """
        if self.serial_connection is not None:
            await self.close()

        try:
            import serial
        except ImportError as exc:
            raise ModbusConnectionError(
                "SerialTransport requires pyserial to be installed."
            ) from exc

        try:
            serial_factory = partial(
                serial.Serial,
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            self.serial_connection = await asyncio.to_thread(
                serial_factory,
            )
        except Exception as exc:
            raise ModbusConnectionError(exc) from exc

    async def close(self) -> None:
        """Close the serial port if it is open."""
        if self.serial_connection is None:
            return

        serial_connection = self.serial_connection
        self.serial_connection = None
        try:
            await asyncio.to_thread(serial_connection.close)
        except Exception:
            pass

    async def send(self, data: bytes) -> None:
        """Write all bytes to the serial port.

        Parameters
        ----------
        data : bytes
            Bytes to write.

        Raises
        ------
        ModbusConnectionError
            If the transport is not connected.
        ModbusTimeoutError
            If the write exceeds ``timeout``.
        ModbusTransportError
            If the serial write fails or writes only part of ``data``.

        """
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
            if _is_serial_timeout_error(exc):
                raise ModbusTimeoutError(exc) from exc
            raise ModbusTransportError(exc) from exc

    async def receive(self, size: int) -> bytes:
        """Read exactly ``size`` bytes from the serial port.

        Parameters
        ----------
        size : int
            Number of bytes to read.

        Returns
        -------
        bytes
            Bytes read from the serial port.

        Raises
        ------
        ValueError
            If ``size`` is not positive.
        ModbusConnectionError
            If the transport is not connected.
        ModbusTimeoutError
            If the read exceeds ``timeout``.
        ModbusTransportError
            If the serial read fails or returns fewer bytes than requested.

        """
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
            raise ModbusTransportError(
                "Serial read returned fewer bytes than requested."
            )
        return data

    @property
    def connected(self) -> bool:
        """Whether the transport is open."""
        return self.serial_connection is not None and self.serial_connection.is_open
