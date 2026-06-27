"""Async TCP transport for Modbus TCP connections."""

import asyncio
from types import TracebackType
from typing import Self

from clear_modbus.constants import DEFAULT_MODBUS_TCP_PORT
from clear_modbus.exceptions import (
    ModbusConnectionError,
    ModbusTimeoutError,
    ModbusTransportError,
)

__all__ = ["TCPTransport"]


class TCPTransport:
    """Asynchronous TCP byte transport.

    Parameters
    ----------
    host : str
        Hostname or IP address to connect to.
    port : int
        TCP port to connect to.
    timeout : float
        Timeout in seconds for connect, send, and receive operations.

    Attributes
    ----------
    host : str
        Hostname or IP address to connect to.
    port : int
        TCP port to connect to.
    timeout : float
        Timeout in seconds for connect, send, and receive operations.

    """

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
        """Open the TCP connection and return this transport.

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
        """Close the TCP connection when leaving an async context."""
        await self.close()

    async def connect(self) -> None:
        """Connect to the configured TCP endpoint.

        Raises
        ------
        ModbusTimeoutError
            If the connection attempt exceeds ``timeout``.
        ModbusConnectionError
            If the socket cannot be opened.

        """
        if self.stream_writer is not None:
            await self.close()
        try:
            async with asyncio.timeout(self.timeout):
                self.stream_reader, self.stream_writer = await asyncio.open_connection(
                    host=self.host, port=self.port
                )
        except TimeoutError as e:
            raise ModbusTimeoutError(e)
        except Exception as e:
            raise ModbusConnectionError(e)

    async def close(self) -> None:
        """Close the connection if it is open.

        Repeated calls are harmless.
        """
        if self.stream_writer is None:
            return
        writer = self.stream_writer
        self.stream_writer = None
        self.stream_reader = None
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    async def send(self, data: bytes) -> None:
        """Write bytes to the TCP stream.

        Parameters
        ----------
        data : bytes
            Bytes to send.

        Raises
        ------
        ModbusConnectionError
            If the transport is not connected.
        ModbusTimeoutError
            If the write cannot complete before ``timeout``.
        ModbusTransportError
            If the stream fails while writing.

        """
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
        """Read exactly ``size`` bytes from the TCP stream.

        Parameters
        ----------
        size : int
            Number of bytes to read.

        Returns
        -------
        bytes
            Bytes read from the stream.

        Raises
        ------
        ValueError
            If ``size`` is not positive.
        ModbusConnectionError
            If the transport is not connected or the connection is lost.
        ModbusTimeoutError
            If the read cannot complete before ``timeout``.
        ModbusTransportError
            If the stream closes before enough bytes are read.

        """
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

    @property
    def connected(self) -> bool:
        """Whether the transport is connected."""
        return self.stream_writer is not None and not self.stream_writer.is_closing()
