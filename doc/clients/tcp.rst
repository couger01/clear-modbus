Modbus TCP Client
=================

Use :class:`clear_modbus.ModbusTcpClient` to connect to a Modbus TCP server.
The client accepts:

* ``host``
* ``port``
* ``unit_id``
* ``timeout``

Read holding registers with an async context manager:

.. code-block:: python

   import asyncio

   from clear_modbus import ModbusTcpClient


   async def main() -> None:
       async with ModbusTcpClient(host="127.0.0.1", port=502, unit_id=1) as client:
           response = await client.read_holding_registers(address=0, count=2)
           print(response.values)


   asyncio.run(main())

Write operations return Modbus echo responses:

.. code-block:: python

   single_register = await client.write_single_register(address=10, value=123)
   multiple_registers = await client.write_multiple_registers(
       address=20,
       values=[100, 200, 300],
   )
   read_after_write = await client.read_write_multiple_registers(
       read_address=0,
       read_count=2,
       write_address=20,
       values=[100, 200],
   )
   masked_register = await client.mask_write_register(
       address=30,
       and_mask=0x00F2,
       or_mask=0x0025,
   )
   single_coil = await client.write_single_coil(address=0, value=True)
   multiple_coils = await client.write_multiple_coils(
       address=1,
       values=[True, False, True],
   )

Each client has a default ``unit_id``. High-level methods also accept
``unit_id`` as a per-call override.

TCP request execution works at a high level like this:

* Create a request PDU.
* Wrap it in an MBAP frame.
* Use the TCP transport to send and receive bytes.
* Validate and decode the response.

Timeouts and Disconnects
------------------------

The TCP transport applies the client ``timeout`` to connect, send, and receive
operations. A timeout raises ``ModbusTimeoutError``. Sending or receiving while
disconnected raises ``ModbusConnectionError``. Other transport failures, such as
short reads, are surfaced as ``ModbusTransportError``.

Repeated ``close()`` calls are intended to be harmless. Transport edge cases are
tracked for further review in issue #3.

API reference: :class:`clear_modbus.ModbusTcpClient`
