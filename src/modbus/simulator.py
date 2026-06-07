"""Local Modbus TCP simulator helpers."""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Self

from modbus.constants import DEFAULT_MODBUS_TCP_PORT
from modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock
from modbus.server import ModbusTcpServer


@dataclass(frozen=True)
class RegisterRange:
    """Register range used to configure simulator profiles.

    Parameters
    ----------
    start_address : int
        First register address.
    values : list[int], optional
        Register values in address order.
    readonly : bool, optional
        Whether writes to this range are rejected.

    Attributes
    ----------
    start_address : int
        First register address.
    values : list[int]
        Register values in address order.
    readonly : bool
        Whether writes to this range are rejected.

    """

    start_address: int
    values: list[int] = field(default_factory=list)
    readonly: bool = False

    def to_block(self) -> RegisterBlock:
        """Convert the range to a datastore register block.

        Returns
        -------
        RegisterBlock
            Datastore block with copied values.

        """
        return RegisterBlock(
            start_address=self.start_address,
            values=list(self.values),
            readonly=self.readonly,
        )


@dataclass(frozen=True)
class BitRange:
    """Bit range used to configure simulator profiles.

    Parameters
    ----------
    start_address : int
        First bit address.
    values : list[bool], optional
        Bit values in address order.
    readonly : bool, optional
        Whether writes to this range are rejected.

    Attributes
    ----------
    start_address : int
        First bit address.
    values : list[bool]
        Bit values in address order.
    readonly : bool
        Whether writes to this range are rejected.

    """

    start_address: int
    values: list[bool] = field(default_factory=list)
    readonly: bool = False

    def to_block(self) -> BitBlock:
        """Convert the range to a datastore bit block.

        Returns
        -------
        BitBlock
            Datastore block with copied values.

        """
        return BitBlock(
            start_address=self.start_address,
            values=list(self.values),
            readonly=self.readonly,
        )


@dataclass(frozen=True)
class SimulatorProfile:
    """Declarative datastore configuration for a simulator."""

    holding_registers: list[RegisterRange] = field(default_factory=list)
    input_registers: list[RegisterRange] = field(default_factory=list)
    coils: list[BitRange] = field(default_factory=list)
    discrete_inputs: list[BitRange] = field(default_factory=list)

    def to_datastore(self) -> MemoryDataStore:
        """Build a memory datastore from this profile.

        Returns
        -------
        MemoryDataStore
            Datastore populated from the configured ranges.

        """
        return MemoryDataStore(
            holding_registers=[item.to_block() for item in self.holding_registers],
            input_registers=[item.to_block() for item in self.input_registers],
            coils=[item.to_block() for item in self.coils],
            discrete_inputs=[item.to_block() for item in self.discrete_inputs],
        )


SimulatorTaskFactory = Callable[[MemoryDataStore], Coroutine[Any, Any, None]]


class ModbusSimulator:
    """Convenience wrapper around a Modbus TCP server and memory datastore.

    Parameters
    ----------
    host : str
        Interface address to bind.
    port : int
        TCP port to bind.
    datastore : MemoryDataStore | None
        Datastore to expose through the simulator.

    Attributes
    ----------
    host : str
        Interface address to bind.
    port : int
        TCP port to bind.
    datastore : MemoryDataStore
        Datastore exposed through the simulator.
    server : ModbusTcpServer
        TCP server backing the simulator.

    """

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
        """Create a simulator from a declarative profile.

        Parameters
        ----------
        profile : SimulatorProfile
            Profile describing simulator data areas.
        host : str, optional
            Interface address to bind.
        port : int, optional
            TCP port to bind.

        Returns
        -------
        ModbusSimulator
            Configured simulator.

        """
        return cls(host=host, port=port, datastore=profile.to_datastore())

    @property
    def bound_port(self) -> int:
        """Return the actual bound TCP port.

        Returns
        -------
        int
            Bound port, useful when the simulator was created with ``port=0``.

        """
        server = self.server._server
        if server is None or not server.sockets:
            return self.port

        socket = server.sockets[0]
        address = socket.getsockname()
        if isinstance(address, tuple):
            return int(address[1])
        return self.port

    async def __aenter__(self) -> Self:
        """Start the simulator and return this instance.

        Returns
        -------
        Self
            Running simulator.

        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Stop the simulator when leaving an async context."""
        await self.stop()

    async def start(self) -> None:
        """Start the TCP server and configured background tasks."""
        await self.server.start()
        self._start_tasks()

    async def stop(self) -> None:
        """Stop background tasks and the TCP server."""
        await self._stop_tasks()
        await self.server.stop()

    def add_task(self, task_factory: SimulatorTaskFactory) -> None:
        """Register a background task factory.

        Parameters
        ----------
        task_factory : SimulatorTaskFactory
            Coroutine factory called with the simulator datastore.

        """
        self._task_factories.append(task_factory)
        if self.server._server is not None:
            self._tasks.append(asyncio.create_task(task_factory(self.datastore)))

    def get_holding_registers(self, address: int, count: int) -> list[int]:
        """Return holding-register values from the simulator datastore.

        Parameters
        ----------
        address : int
            First holding-register address.
        count : int
            Number of registers to read.

        Returns
        -------
        list[int]
            Register values.

        """
        return self.datastore.get_holding_registers(address, count)

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        """Write holding-register values in the simulator datastore."""
        self.datastore.set_holding_registers(address, values)

    def get_input_registers(self, address: int, count: int) -> list[int]:
        """Return input-register values from the simulator datastore.

        Parameters
        ----------
        address : int
            First input-register address.
        count : int
            Number of registers to read.

        Returns
        -------
        list[int]
            Register values.

        """
        return self.datastore.get_input_registers(address, count)

    def set_input_registers(self, address: int, values: list[int]) -> None:
        """Write input-register values in the simulator datastore."""
        block = self.datastore._find_register_block(
            self.datastore.input_registers,
            address,
            len(values),
        )
        block.write(address, values)

    def get_coils(self, address: int, count: int) -> list[bool]:
        """Return coil values from the simulator datastore.

        Parameters
        ----------
        address : int
            First coil address.
        count : int
            Number of coils to read.

        Returns
        -------
        list[bool]
            Coil values.

        """
        return self.datastore.get_coils(address, count)

    def set_coils(self, address: int, values: list[bool]) -> None:
        """Write coil values in the simulator datastore."""
        self.datastore.set_coils(address, values)

    def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
        """Return discrete-input values from the simulator datastore.

        Parameters
        ----------
        address : int
            First discrete-input address.
        count : int
            Number of inputs to read.

        Returns
        -------
        list[bool]
            Discrete-input values.

        """
        return self.datastore.get_discrete_inputs(address, count)

    def set_discrete_inputs(self, address: int, values: list[bool]) -> None:
        """Write discrete-input values in the simulator datastore."""
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
