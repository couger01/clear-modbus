import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

from modbus.constants import DEFAULT_MODBUS_TCP_PORT
from modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock
from modbus.server import ModbusTcpServer


@dataclass(frozen=True)
class RegisterRange:
    start_address: int
    values: list[int] = field(default_factory=list)
    readonly: bool = False

    def to_block(self) -> RegisterBlock:
        return RegisterBlock(
            start_address=self.start_address,
            values=list(self.values),
            readonly=self.readonly,
        )


@dataclass(frozen=True)
class BitRange:
    start_address: int
    values: list[bool] = field(default_factory=list)
    readonly: bool = False

    def to_block(self) -> BitBlock:
        return BitBlock(
            start_address=self.start_address,
            values=list(self.values),
            readonly=self.readonly,
        )


@dataclass(frozen=True)
class SimulatorProfile:
    holding_registers: list[RegisterRange] = field(default_factory=list)
    input_registers: list[RegisterRange] = field(default_factory=list)
    coils: list[BitRange] = field(default_factory=list)
    discrete_inputs: list[BitRange] = field(default_factory=list)

    def to_datastore(self) -> MemoryDataStore:
        return MemoryDataStore(
            holding_registers=[item.to_block() for item in self.holding_registers],
            input_registers=[item.to_block() for item in self.input_registers],
            coils=[item.to_block() for item in self.coils],
            discrete_inputs=[item.to_block() for item in self.discrete_inputs],
        )


SimulatorTaskFactory = Callable[[MemoryDataStore], Awaitable[None]]


class ModbusSimulator:
    host: str
    port: int
    datastore: MemoryDataStore
    server: ModbusTcpServer

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_MODBUS_TCP_PORT,
        datastore: MemoryDataStore | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.datastore = datastore if datastore is not None else MemoryDataStore()
        self.server = ModbusTcpServer(
            host=self.host,
            port=self.port,
            datastore=self.datastore,
        )
        self._task_factories: list[SimulatorTaskFactory] = []
        self._tasks: list[asyncio.Task[None]] = []

    @classmethod
    def from_profile(
        cls,
        profile: SimulatorProfile,
        *,
        host: str = "127.0.0.1",
        port: int = DEFAULT_MODBUS_TCP_PORT,
    ) -> "ModbusSimulator":
        return cls(host=host, port=port, datastore=profile.to_datastore())

    @property
    def bound_port(self) -> int:
        server = self.server._server
        if server is None or not server.sockets:
            return self.port

        socket = server.sockets[0]
        address = socket.getsockname()
        if isinstance(address, tuple):
            return int(address[1])
        return self.port

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
        await self.server.start()
        self._start_tasks()

    async def stop(self) -> None:
        await self._stop_tasks()
        await self.server.stop()

    def add_task(self, task_factory: SimulatorTaskFactory) -> None:
        self._task_factories.append(task_factory)
        if self.server._server is not None:
            self._tasks.append(asyncio.create_task(task_factory(self.datastore)))

    def get_holding_registers(self, address: int, count: int) -> list[int]:
        return self.datastore.get_holding_registers(address, count)

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        self.datastore.set_holding_registers(address, values)

    def get_input_registers(self, address: int, count: int) -> list[int]:
        return self.datastore.get_input_registers(address, count)

    def set_input_registers(self, address: int, values: list[int]) -> None:
        block = self.datastore._find_register_block(
            self.datastore.input_registers,
            address,
            len(values),
        )
        block.write(address, values)

    def get_coils(self, address: int, count: int) -> list[bool]:
        return self.datastore.get_coils(address, count)

    def set_coils(self, address: int, values: list[bool]) -> None:
        self.datastore.set_coils(address, values)

    def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
        return self.datastore.get_discrete_inputs(address, count)

    def set_discrete_inputs(self, address: int, values: list[bool]) -> None:
        block = self.datastore._find_bit_block(
            self.datastore.discrete_inputs,
            address,
            len(values),
        )
        block.write(address, values)

    def _start_tasks(self) -> None:
        if self._tasks:
            return

        for task_factory in self._task_factories:
            self._tasks.append(asyncio.create_task(task_factory(self.datastore)))

    async def _stop_tasks(self) -> None:
        if not self._tasks:
            return

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
