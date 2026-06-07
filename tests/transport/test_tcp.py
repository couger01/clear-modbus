import asyncio

import pytest

from clear_modbus.constants import DEFAULT_MODBUS_TCP_PORT
from clear_modbus.exceptions import (
    ModbusConnectionError,
    ModbusTimeoutError,
    ModbusTransportError,
)
from clear_modbus.transport.tcp import TCPTransport


class FakeStreamWriter:
    def __init__(
        self,
        *,
        write_error: Exception | None = None,
        drain_error: Exception | None = None,
        wait_closed_error: Exception | None = None,
    ) -> None:
        self.writes: list[bytes] = []
        self.closed = False
        self.drain_called = False
        self.wait_closed_called = False
        self.write_error = write_error
        self.drain_error = drain_error
        self.wait_closed_error = wait_closed_error

    def write(self, data: bytes) -> None:
        if self.write_error is not None:
            raise self.write_error
        self.writes.append(data)

    async def drain(self) -> None:
        self.drain_called = True
        if self.drain_error is not None:
            raise self.drain_error

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.wait_closed_called = True
        if self.wait_closed_error is not None:
            raise self.wait_closed_error


class FakeStreamReader:
    def __init__(
        self,
        data: bytes = b"",
        *,
        read_error: Exception | None = None,
    ) -> None:
        self.data = data
        self.read_sizes: list[int] = []
        self.read_error = read_error

    async def readexactly(self, size: int) -> bytes:
        self.read_sizes.append(size)
        if self.read_error is not None:
            raise self.read_error
        return self.data


def test_tcp_transport_initializes_connection_settings() -> None:
    transport = TCPTransport(host="127.0.0.1", port=DEFAULT_MODBUS_TCP_PORT, timeout=5)

    assert transport.host == "127.0.0.1"
    assert transport.port == DEFAULT_MODBUS_TCP_PORT
    assert transport.timeout == 5
    assert transport.stream_reader is None
    assert transport.stream_writer is None


@pytest.mark.asyncio
async def test_tcp_transport_async_context_manager_connects_and_closes(
    monkeypatch,
) -> None:
    reader = FakeStreamReader()
    writer = FakeStreamWriter()

    async def fake_open_connection(*, host: str, port: int):
        assert host == "127.0.0.1"
        assert port == DEFAULT_MODBUS_TCP_PORT
        return reader, writer

    monkeypatch.setattr(
        "clear_modbus.transport.tcp.asyncio.open_connection", fake_open_connection
    )

    async with TCPTransport(host="127.0.0.1") as transport:
        assert transport.stream_reader is reader
        assert transport.stream_writer is writer
        assert writer.closed is False

    assert writer.closed is True
    assert writer.wait_closed_called is True
    assert transport.stream_reader is None
    assert transport.stream_writer is None


@pytest.mark.asyncio
async def test_connect_opens_streams(monkeypatch) -> None:
    reader = FakeStreamReader()
    writer = FakeStreamWriter()

    async def fake_open_connection(*, host: str, port: int):
        return reader, writer

    monkeypatch.setattr(
        "clear_modbus.transport.tcp.asyncio.open_connection", fake_open_connection
    )

    transport = TCPTransport(host="127.0.0.1")

    await transport.connect()

    assert transport.stream_reader is reader
    assert transport.stream_writer is writer


@pytest.mark.asyncio
async def test_connect_wraps_timeout_errors(monkeypatch) -> None:
    async def fake_open_connection(*, host: str, port: int):
        raise TimeoutError()

    monkeypatch.setattr(
        "clear_modbus.transport.tcp.asyncio.open_connection", fake_open_connection
    )

    transport = TCPTransport(host="127.0.0.1")

    with pytest.raises(ModbusTimeoutError):
        await transport.connect()


@pytest.mark.asyncio
async def test_connect_wraps_open_connection_errors(monkeypatch) -> None:
    async def fake_open_connection(*, host: str, port: int):
        raise OSError("connection refused")

    monkeypatch.setattr(
        "clear_modbus.transport.tcp.asyncio.open_connection", fake_open_connection
    )

    transport = TCPTransport(host="127.0.0.1")

    with pytest.raises(ModbusConnectionError):
        await transport.connect()


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:
    transport = TCPTransport(host="127.0.0.1")

    await transport.close()

    writer = FakeStreamWriter()
    reader = FakeStreamReader()
    transport.stream_writer = writer
    transport.stream_reader = reader

    await transport.close()
    await transport.close()

    assert writer.closed is True
    assert writer.wait_closed_called is True
    assert transport.stream_writer is None
    assert transport.stream_reader is None


@pytest.mark.asyncio
async def test_close_ignores_wait_closed_errors_and_clears_state() -> None:
    transport = TCPTransport(host="127.0.0.1")
    writer = FakeStreamWriter(wait_closed_error=OSError("close failed"))
    transport.stream_writer = writer
    transport.stream_reader = FakeStreamReader()

    await transport.close()

    assert writer.closed is True
    assert writer.wait_closed_called is True
    assert transport.stream_writer is None
    assert transport.stream_reader is None


@pytest.mark.asyncio
async def test_send_writes_and_drains() -> None:
    transport = TCPTransport(host="127.0.0.1")
    writer = FakeStreamWriter()
    transport.stream_writer = writer

    await transport.send(bytes.fromhex("01 02 03"))

    assert writer.writes == [bytes.fromhex("01 02 03")]
    assert writer.drain_called is True


@pytest.mark.asyncio
async def test_send_rejects_disconnected_transport() -> None:
    transport = TCPTransport(host="127.0.0.1")

    with pytest.raises(ModbusConnectionError):
        await transport.send(b"data")


@pytest.mark.asyncio
async def test_send_wraps_drain_timeout_and_keeps_stream() -> None:
    transport = TCPTransport(host="127.0.0.1")
    writer = FakeStreamWriter(drain_error=TimeoutError())
    transport.stream_writer = writer

    with pytest.raises(ModbusTimeoutError):
        await transport.send(b"data")

    assert writer.writes == [b"data"]
    assert transport.stream_writer is writer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "writer",
    [
        FakeStreamWriter(write_error=OSError("write failed")),
        FakeStreamWriter(drain_error=OSError("drain failed")),
    ],
)
async def test_send_wraps_stream_errors_and_keeps_stream(
    writer: FakeStreamWriter,
) -> None:
    transport = TCPTransport(host="127.0.0.1")
    transport.stream_writer = writer

    with pytest.raises(ModbusTransportError):
        await transport.send(b"data")

    assert transport.stream_writer is writer


@pytest.mark.asyncio
async def test_receive_reads_exactly_requested_size() -> None:
    transport = TCPTransport(host="127.0.0.1")
    reader = FakeStreamReader(data=bytes.fromhex("01 02 03"))
    transport.stream_reader = reader

    data = await transport.receive(3)

    assert data == bytes.fromhex("01 02 03")
    assert reader.read_sizes == [3]


@pytest.mark.asyncio
async def test_receive_rejects_non_positive_size() -> None:
    transport = TCPTransport(host="127.0.0.1")
    transport.stream_reader = FakeStreamReader()

    with pytest.raises(ValueError):
        await transport.receive(0)

    with pytest.raises(ValueError):
        await transport.receive(-1)


@pytest.mark.asyncio
async def test_receive_wraps_timeout_errors() -> None:
    transport = TCPTransport(host="127.0.0.1")
    transport.stream_reader = FakeStreamReader(read_error=TimeoutError())

    with pytest.raises(ModbusTimeoutError):
        await transport.receive(1)


@pytest.mark.asyncio
async def test_receive_wraps_incomplete_reads() -> None:
    transport = TCPTransport(host="127.0.0.1")
    transport.stream_reader = FakeStreamReader(
        read_error=asyncio.IncompleteReadError(partial=b"", expected=1)
    )

    with pytest.raises(ModbusTransportError):
        await transport.receive(1)


@pytest.mark.asyncio
async def test_receive_wraps_connection_resets() -> None:
    transport = TCPTransport(host="127.0.0.1")
    transport.stream_reader = FakeStreamReader(read_error=ConnectionResetError())

    with pytest.raises(ModbusConnectionError):
        await transport.receive(1)
