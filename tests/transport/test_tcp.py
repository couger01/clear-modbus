import pytest

from modbus.constants import DEFAULT_MODBUS_TCP_PORT
from modbus.exceptions import ModbusConnectionError, ModbusTimeoutError
from modbus.transport.tcp import TCPTransport


class FakeStreamWriter:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.closed = False
        self.drain_called = False
        self.wait_closed_called = False

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        self.drain_called = True

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.wait_closed_called = True


class FakeStreamReader:
    def __init__(self, data: bytes = b"") -> None:
        self.data = data
        self.read_sizes: list[int] = []

    async def readexactly(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return self.data


def test_tcp_transport_initializes_connection_settings() -> None:
    transport = TCPTransport(host="127.0.0.1", port=DEFAULT_MODBUS_TCP_PORT, timeout=5)

    assert transport.host == "127.0.0.1"
    assert transport.port == DEFAULT_MODBUS_TCP_PORT
    assert transport.timeout == 5
    assert transport.stream_reader is None
    assert transport.stream_writer is None


@pytest.mark.asyncio
async def test_tcp_transport_async_context_manager_connects_and_closes(monkeypatch) -> None:
    reader = FakeStreamReader()
    writer = FakeStreamWriter()

    async def fake_open_connection(*, host: str, port: int):
        assert host == "127.0.0.1"
        assert port == DEFAULT_MODBUS_TCP_PORT
        return reader, writer

    monkeypatch.setattr("modbus.transport.tcp.asyncio.open_connection", fake_open_connection)

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

    monkeypatch.setattr("modbus.transport.tcp.asyncio.open_connection", fake_open_connection)

    transport = TCPTransport(host="127.0.0.1")

    await transport.connect()

    assert transport.stream_reader is reader
    assert transport.stream_writer is writer


@pytest.mark.asyncio
async def test_connect_wraps_timeout_errors(monkeypatch) -> None:
    async def fake_open_connection(*, host: str, port: int):
        raise TimeoutError()

    monkeypatch.setattr("modbus.transport.tcp.asyncio.open_connection", fake_open_connection)

    transport = TCPTransport(host="127.0.0.1")

    with pytest.raises(ModbusTimeoutError):
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
