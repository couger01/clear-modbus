Simulator
=========

Use :class:`clear_modbus.ModbusSimulator` for local development and tests that
need a lightweight Modbus TCP endpoint. The simulator wraps
:class:`clear_modbus.server.ModbusTcpServer` and
:class:`clear_modbus.datastore.MemoryDataStore` so tests can define values,
start a server, connect a client, and then tear everything down with async
context managers.

Profiles
--------

``SimulatorProfile`` provides a declarative way to configure simulator data
areas:

.. code-block:: python

   from clear_modbus import BitRange, ModbusSimulator, RegisterRange, SimulatorProfile

   simulator = ModbusSimulator.from_profile(
       SimulatorProfile(
           holding_registers=[
               RegisterRange(start_address=0, values=[10, 20]),
           ],
           input_registers=[
               RegisterRange(start_address=100, values=[30, 40], readonly=True),
           ],
           coils=[
               BitRange(start_address=0, values=[True, False]),
           ],
           discrete_inputs=[
               BitRange(start_address=100, values=[False, True], readonly=True),
           ],
           device_identification={
               0: "Example Vendor",
               1: "Example Product",
               2: "1.0.0",
           },
       ),
       port=0,
   )

The ``device_identification`` mapping configures objects returned by Read
Device Identification requests. Object values may be ``bytes`` or strings.

Use ``port=0`` when tests need the operating system to choose an available TCP
port. After the simulator starts, ``bound_port`` returns the actual port:

.. code-block:: python

   async with simulator:
       print(simulator.bound_port)

Background Tasks
----------------

Background tasks can mutate simulator values while clients are connected. A
task factory receives the simulator datastore and returns a coroutine:

.. code-block:: python

   import asyncio

   from clear_modbus.datastore import MemoryDataStore


   async def increment_counter(datastore: MemoryDataStore) -> None:
       while True:
           value = datastore.get_holding_registers(address=0, count=1)[0]
           datastore.set_holding_registers(address=0, values=[value + 1])
           await asyncio.sleep(1.0)


   simulator.add_task(increment_counter)

Tasks are started when the simulator starts and cancelled when the simulator
stops.

Direct Datastore Helpers
------------------------

The simulator exposes convenience methods for updating and reading its backing
datastore:

* ``get_holding_registers()`` and ``set_holding_registers()``
* ``get_input_registers()`` and ``set_input_registers()``
* ``get_coils()`` and ``set_coils()``
* ``get_discrete_inputs()`` and ``set_discrete_inputs()``

These helpers are useful in tests when the expected device state changes during
the test.

Testing Pattern
---------------

A typical simulator test starts the simulator, connects a client to
``simulator.host`` and ``simulator.bound_port``, asserts client-visible values,
and then exits the async contexts:

.. code-block:: python

   from clear_modbus import ModbusTcpClient

   async with simulator:
       async with ModbusTcpClient(
           host=simulator.host,
           port=simulator.bound_port,
       ) as client:
           response = await client.read_holding_registers(address=0, count=2)
           assert response.values == [10, 20]

API reference: :class:`clear_modbus.ModbusSimulator`,
:class:`clear_modbus.SimulatorProfile`, :class:`clear_modbus.RegisterRange`,
and :class:`clear_modbus.BitRange`
