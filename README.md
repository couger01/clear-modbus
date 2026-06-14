# clear-modbus

An async Python Modbus toolkit for building clients, servers, and lightweight
simulators.

This project currently supports Modbus TCP and Modbus RTU, typed request and
response PDUs, in-memory datastore blocks, and a TCP simulator for local
integration testing.

## Status

This is an early `0.1` release. The core API is usable, but it should still be
treated as a young library: expect the public API to tighten as real device
usage and integration feedback accumulate.

## Features

- Async Modbus TCP client
- Async Modbus RTU client
- Async Modbus TCP server
- TCP simulator backed by an in-memory datastore
- MBAP and RTU frame encoding/decoding
- Modbus exception response handling
- Function code support for:
  - Read coils (`0x01`)
  - Read discrete inputs (`0x02`)
  - Read holding registers (`0x03`)
  - Read input registers (`0x04`)
  - Write single coil (`0x05`)
  - Write single register (`0x06`)
  - Write multiple coils (`0x0F`)
  - Write multiple registers (`0x10`)
  - Read/write multiple registers (`0x17`)

## Requirements

- Python 3.12+
- `pyserial` for RTU serial transport

## Installation

Install the package:

```bash
pip install clear-modbus
```

For local development:

```bash
uv sync --dev
```

The distribution package is `clear-modbus`; the Python import package is
`clear_modbus`:

```python
import clear_modbus
```

## Modbus TCP Client

```python
import asyncio

from clear_modbus import ModbusTcpClient


async def main() -> None:
    async with ModbusTcpClient(host="127.0.0.1", port=502, unit_id=1) as client:
        response = await client.read_holding_registers(address=0, count=2)
        print(response.values)


asyncio.run(main())
```

### Write Registers

```python
import asyncio

from clear_modbus import ModbusTcpClient


async def main() -> None:
    async with ModbusTcpClient(host="127.0.0.1", port=502, unit_id=1) as client:
        single = await client.write_single_register(address=10, value=123)
        multiple = await client.write_multiple_registers(
            address=20,
            values=[100, 200, 300],
        )
        read_after_write = await client.read_write_multiple_registers(
            read_address=0,
            read_count=2,
            write_address=20,
            values=[100, 200],
        )

    print(single.address, single.value)
    print(multiple.address, multiple.count)


asyncio.run(main())
```

### Coils and Discrete Inputs

```python
import asyncio

from clear_modbus import ModbusTcpClient


async def main() -> None:
    async with ModbusTcpClient(host="127.0.0.1", port=502, unit_id=1) as client:
        await client.write_single_coil(address=0, value=True)
        await client.write_multiple_coils(address=1, values=[True, False, True])

        coils = await client.read_coils(address=0, count=4)
        inputs = await client.read_discrete_inputs(address=0, count=4)

    print(coils.values)
    print(inputs.values)


asyncio.run(main())
```

## Modbus RTU Client

```python
import asyncio

from clear_modbus import ModbusRtuClient


async def main() -> None:
    async with ModbusRtuClient(
        port="/dev/ttyUSB0",
        unit_id=1,
        baudrate=9600,
        timeout=1.0,
    ) as client:
        response = await client.read_input_registers(address=0, count=2)
        print(response.values)


asyncio.run(main())
```

## Simulator

The simulator is useful for tests, examples, and local development without a
physical device.

```python
import asyncio

from clear_modbus import (
    ModbusSimulator,
    ModbusTcpClient,
    RegisterRange,
    SimulatorProfile,
)


async def main() -> None:
    simulator = ModbusSimulator.from_profile(
        SimulatorProfile(
            holding_registers=[
                RegisterRange(start_address=0, values=[10, 20]),
            ],
        ),
        port=0,
    )

    async with simulator:
        async with ModbusTcpClient(
            host=simulator.host,
            port=simulator.bound_port,
        ) as client:
            response = await client.read_holding_registers(address=0, count=2)

    print(response.values)


asyncio.run(main())
```

### Simulator Background Tasks

Background tasks can mutate the simulator datastore while clients interact with
it.

```python
import asyncio

from clear_modbus import (
    ModbusSimulator,
    ModbusTcpClient,
    RegisterRange,
    SimulatorProfile,
)
from clear_modbus.datastore import MemoryDataStore


async def increment_counter(datastore: MemoryDataStore) -> None:
    while True:
        value = datastore.get_holding_registers(address=0, count=1)[0]
        datastore.set_holding_registers(address=0, values=[value + 1])
        await asyncio.sleep(1.0)


async def main() -> None:
    simulator = ModbusSimulator.from_profile(
        SimulatorProfile(
            holding_registers=[
                RegisterRange(start_address=0, values=[0]),
            ],
        ),
        port=0,
    )
    simulator.add_task(increment_counter)

    async with simulator:
        async with ModbusTcpClient(
            host=simulator.host,
            port=simulator.bound_port,
        ) as client:
            response = await client.read_holding_registers(address=0, count=1)

    print(response.values)


asyncio.run(main())
```

## Handling Exception Responses

High-level client helpers raise `ModbusExceptionResponseError` when a server
returns a valid Modbus exception response.

```python
from clear_modbus import ModbusExceptionResponseError

try:
    response = await client.read_holding_registers(address=0, count=2)
except ModbusExceptionResponseError as exc:
    print(exc.function_code, exc.exception_code)
```

Low-level `execute()` calls return the decoded response PDU directly, including
exception response PDUs, so callers can decide how to handle them.

## Datastore

Servers and simulators use in-memory register and bit blocks.

```python
from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock

datastore = MemoryDataStore(
    holding_registers=[
        RegisterBlock(start_address=0, values=[10, 20]),
    ],
    coils=[
        BitBlock(start_address=100, values=[True, False]),
    ],
)
```

## Development

Run the test suite:

```bash
uv run pytest
```

Run formatting, linting, and type checks:

```bash
uv run pre-commit run --all-files
```

Build the package:

```bash
uv build
```

Smoke test the built wheel in a temporary virtual environment:

```bash
uv build
python scripts/smoke_wheel.py
```

## Current Limitations

- Async API only
- No Modbus ASCII support yet
- No UDP or TLS transport yet
- No custom function-code registry yet
