Getting Started
===============

clear-modbus is an async Python library for writing code that manages Modbus
devices. It is intended to be useful both for learning the Modbus protocol and
for building applications with versioned, semver-oriented APIs.

The current release supports:

   - Async Modbus TCP and RTU clients
   - Async Modbus TCP server
   - Modbus TCP simulator
   - In-memory datastore blocks

Install the package with:

.. code-block:: bash

   pip install clear-modbus

Set up a local development environment with:

.. code-block:: bash

   uv sync --dev

The distribution package is named ``clear-modbus``. The Python import package
is named ``clear_modbus``.

The smallest practical TCP client example uses an async context manager so the
transport is opened and closed cleanly:

.. code-block:: python

   import asyncio

   from clear_modbus import ModbusTcpClient


   async def main() -> None:
       async with ModbusTcpClient(host="127.0.0.1", port=502) as client:
           response = await client.read_holding_registers(address=0, count=2)
           print(response.values)


   asyncio.run(main())

clear-modbus uses ``asyncio``. Client, server, and simulator code should run
inside an event loop, and the async context manager APIs should be preferred so
network and serial resources are closed predictably.

For more detail, see:

- :doc:`Clients <clients/index>`
- :doc:`Server <server>`
- :doc:`Simulator <simulator>`
- :doc:`API reference <api>`
