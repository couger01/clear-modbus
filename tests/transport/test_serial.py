import pytest

from clear_modbus.exceptions import ModbusConnectionError
from clear_modbus.transport.serial import SerialTransport


def test_serial_transport_initializes_connection_settings() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0", baudrate=19200, timeout=2)

    assert transport.port == "/dev/ttyUSB0"
    assert transport.baudrate == 19200
    assert transport.timeout == 2
    assert transport.serial_connection is None


@pytest.mark.asyncio
async def test_serial_transport_close_is_idempotent() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")

    await transport.close()
    await transport.close()

    assert transport.serial_connection is None


@pytest.mark.asyncio
async def test_serial_transport_send_rejects_disconnected_transport() -> None:
    transport = SerialTransport(port="/dev/ttyUSB0")

    with pytest.raises(ModbusConnectionError):
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
