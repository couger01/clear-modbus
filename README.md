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

## Current Limitations

- Async API only
- No Modbus ASCII support yet
- No UDP or TLS transport yet
- No custom function-code registry yet
- Public package/distribution name is not finalized
