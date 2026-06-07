import asyncio

import pytest

from clear_modbus import ModbusTcpClient
from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock
from clear_modbus.simulator import (
    BitRange,
    ModbusSimulator,
    RegisterRange,
    SimulatorProfile,
)


def test_simulator_profile_builds_memory_datastore() -> None:
    profile = SimulatorProfile(
        holding_registers=[RegisterRange(start_address=0, values=[10, 20])],
        input_registers=[RegisterRange(start_address=100, values=[30])],
        coils=[BitRange(start_address=200, values=[True, False])],
        discrete_inputs=[BitRange(start_address=300, values=[False])],
    )

    datastore = profile.to_datastore()

    assert datastore.get_holding_registers(0, 2) == [10, 20]
    assert datastore.get_input_registers(100, 1) == [30]
    assert datastore.get_coils(200, 2) == [True, False]
    assert datastore.get_discrete_inputs(300, 1) == [False]


def test_simulator_uses_supplied_datastore() -> None:
    datastore = MemoryDataStore(
        holding_registers=[RegisterBlock(start_address=0, values=[10])]
    )

    simulator = ModbusSimulator(datastore=datastore)

    assert simulator.datastore is datastore
    assert simulator.server.datastore is datastore


def test_simulator_from_profile_configures_server_and_datastore() -> None:
    simulator = ModbusSimulator.from_profile(
        SimulatorProfile(
            holding_registers=[RegisterRange(start_address=0, values=[10])]
        ),
        host="127.0.0.1",
        port=1502,
    )

    assert simulator.host == "127.0.0.1"
    assert simulator.port == 1502
    assert simulator.get_holding_registers(0, 1) == [10]
    assert simulator.server.datastore is simulator.datastore


def test_simulator_helpers_read_and_write_datastore_values() -> None:
    simulator = ModbusSimulator(
        datastore=MemoryDataStore(
            holding_registers=[RegisterBlock(start_address=0, values=[10])],
            input_registers=[RegisterBlock(start_address=100, values=[20])],
            coils=[BitBlock(start_address=200, values=[False])],
            discrete_inputs=[BitBlock(start_address=300, values=[True])],
        )
    )

    simulator.set_holding_registers(0, [11])
    simulator.set_input_registers(100, [21])
    simulator.set_coils(200, [True])
    simulator.set_discrete_inputs(300, [False])

    assert simulator.get_holding_registers(0, 1) == [11]
    assert simulator.get_input_registers(100, 1) == [21]
    assert simulator.get_coils(200, 1) == [True]
    assert simulator.get_discrete_inputs(300, 1) == [False]


@pytest.mark.asyncio
async def test_simulator_context_manager_starts_and_stops_server() -> None:
    simulator = ModbusSimulator(port=0)

    async with simulator:
        assert simulator.server._server is not None
        assert simulator.bound_port > 0

    assert simulator.server._server is None


@pytest.mark.asyncio
async def test_simulator_serves_modbus_tcp_client_requests() -> None:
    simulator = ModbusSimulator.from_profile(
        SimulatorProfile(
            holding_registers=[RegisterRange(start_address=0, values=[10, 20])]
        ),
        port=0,
    )

    async with simulator:
        async with ModbusTcpClient(
            host=simulator.host, port=simulator.bound_port
        ) as client:
            response = await client.read_holding_registers(address=0, count=2)

    assert response.values == [10, 20]


@pytest.mark.asyncio
async def test_simulator_runs_and_cancels_background_tasks() -> None:
    started = asyncio.Event()
    simulator = ModbusSimulator(
        port=0,
        datastore=MemoryDataStore(
            holding_registers=[RegisterBlock(start_address=0, values=[10])]
        ),
    )

    async def update_register(datastore: MemoryDataStore) -> None:
        datastore.set_holding_registers(0, [99])
        started.set()
        await asyncio.Event().wait()

    simulator.add_task(update_register)

    async with simulator:
        await asyncio.wait_for(started.wait(), timeout=1)
        assert simulator.get_holding_registers(0, 1) == [99]
        assert len(simulator._tasks) == 1

    assert simulator._tasks == []
