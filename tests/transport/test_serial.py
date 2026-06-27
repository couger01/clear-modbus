import sys
from types import SimpleNamespace

import pytest
import serial

from clear_modbus.exceptions import (
    ModbusConnectionError,
    ModbusTimeoutError,
    ModbusTransportError,
)
from clear_modbus.transport.serial import SerialTransport


class FakeSerialConnection:
    def __init__(
        self,
        *,
        write_result: int | None = None,
        write_error: Exception | None = None,
        read_data: bytes = b"",
        read_error: Exception | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.write_result = write_result
        self.write_error = write_error
        self.read_data = read_data
        self.read_error = read_error
        self.close_error = close_error
        self.writes: list[bytes] = []
        self.read_sizes: list[int] = []
        self.closed = False
        self.is_open = True

    def write(self, data: bytes) -> int:
        if self.write_error is not None:
            raise self.write_error
        self.writes.append(data)
        if self.write_result is not None:
            return self.write_result
        return len(data)

    def read(self, size: int) -> bytes:
        if self.read_error is not None:
            raise self.read_error
        self.read_sizes.append(size)
        return self.read_data

    def close(self) -> None:
        self.closed = True
        self.is_open = False
        if self.close_error is not None:
            raise self.close_error


def test_serial_transport_initializes_connection_settings() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0", baudrate=19200, timeout=2)

    assert transport.port == "/dev/ttyUSB0"
    assert transport.baudrate == 19200
    assert transport.timeout == 2
    assert transport.serial_connection is None
    assert transport.connected is False


def test_serial_transport_connected_reflects_serial_state() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    serial_connection = FakeSerialConnection()
    transport.serial_connection = serial_connection

    assert transport.connected is True

    serial_connection.close()

    assert transport.connected is False


@pytest.mark.asyncio
async def test_serial_transport_close_is_idempotent() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")

    await transport.close()
    await transport.close()

    assert transport.serial_connection is None


@pytest.mark.asyncio
async def test_serial_transport_close_ignores_errors_and_clears_state() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    serial_connection = FakeSerialConnection(close_error=OSError("close failed"))
    transport.serial_connection = serial_connection

    await transport.close()

    assert serial_connection.closed is True
    assert transport.serial_connection is None


@pytest.mark.asyncio
async def test_serial_transport_connect_wraps_missing_pyserial(monkeypatch) -> None:
    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "serial":
            raise ImportError("missing serial")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    transport = SerialTransport(port="/dev/ttyUSB0")

    with pytest.raises(ModbusConnectionError):
        await transport.connect()


@pytest.mark.asyncio
async def test_serial_transport_connect_wraps_open_errors(monkeypatch) -> None:
    class FailingSerial:
        def __init__(self, **kwargs) -> None:
            raise OSError("open failed")

    monkeypatch.setitem(sys.modules, "serial", SimpleNamespace(Serial=FailingSerial))

    transport = SerialTransport(port="/dev/ttyUSB0")

    with pytest.raises(ModbusConnectionError):
        await transport.connect()


@pytest.mark.asyncio
async def test_serial_transport_send_rejects_disconnected_transport() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")

    with pytest.raises(ModbusConnectionError):
        await transport.send(b"data")


@pytest.mark.asyncio
async def test_serial_transport_send_writes_all_bytes() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    serial_connection = FakeSerialConnection()
    transport.serial_connection = serial_connection

    await transport.send(bytes.fromhex("01 02 03"))

    assert serial_connection.writes == [bytes.fromhex("01 02 03")]


@pytest.mark.asyncio
async def test_serial_transport_send_wraps_write_timeout() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = FakeSerialConnection(
        write_error=serial.SerialTimeoutException()
    )

    with pytest.raises(ModbusTimeoutError):
        await transport.send(b"data")


@pytest.mark.asyncio
async def test_serial_transport_send_rejects_partial_writes() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = FakeSerialConnection(write_result=2)

    with pytest.raises(ModbusTransportError):
        await transport.send(b"data")


@pytest.mark.asyncio
async def test_serial_transport_send_wraps_write_errors() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = FakeSerialConnection(write_error=OSError("failed"))

    with pytest.raises(ModbusTransportError):
        await transport.send(b"data")


@pytest.mark.asyncio
async def test_serial_transport_receive_rejects_disconnected_transport() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")

    with pytest.raises(ModbusConnectionError):
        await transport.receive(1)


@pytest.mark.asyncio
async def test_serial_transport_receive_rejects_non_positive_size() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = object()

    with pytest.raises(ValueError):
        await transport.receive(0)


@pytest.mark.asyncio
async def test_serial_transport_receive_reads_exactly_requested_size() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    serial_connection = FakeSerialConnection(read_data=bytes.fromhex("01 02 03"))
    transport.serial_connection = serial_connection

    data = await transport.receive(3)

    assert data == bytes.fromhex("01 02 03")
    assert serial_connection.read_sizes == [3]


@pytest.mark.asyncio
async def test_serial_transport_receive_wraps_read_timeout() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = FakeSerialConnection(read_error=TimeoutError())

    with pytest.raises(ModbusTimeoutError):
        await transport.receive(1)


@pytest.mark.asyncio
async def test_serial_transport_receive_rejects_short_reads() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = FakeSerialConnection(read_data=b"")

    with pytest.raises(ModbusTransportError):
        await transport.receive(1)


@pytest.mark.asyncio
async def test_serial_transport_receive_wraps_read_errors() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")
    transport.serial_connection = FakeSerialConnection(read_error=OSError("failed"))

    with pytest.raises(ModbusTransportError):
        await transport.receive(1)
